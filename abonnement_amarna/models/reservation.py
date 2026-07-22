# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import datetime, time, timedelta
from odoo.exceptions import ValidationError


class AmarnaClubReservation(models.Model):
    _name = 'amarna.club.reservation'
    _description = 'Réservation ponctuelle du club'
    _order = 'start_at desc'

    name = fields.Char(string='Référence / titre', required=True, default='Nouveau', copy=False)
    mobile_activity_code = fields.Char(string='Code activité mobile')
    activity_id = fields.Many2one('amarna.club.activity', string='Activité', compute='_compute_activity_id', store=True, readonly=False)
    client_name = fields.Char(string='Nom du client')
    partner_id = fields.Many2one('res.partner', string='Membre / client')
    subscription_id = fields.Many2one('amarna.subscription', string='Abonnement utilisé')
    rfid_card_id = fields.Many2one('amarna.rfid.card', string='Carte RFID', ondelete='set null')
    reservation_date = fields.Date(string='Date de réservation', default=fields.Date.today)
    start_hour = fields.Float(string='Heure de début', help='Heure au format décimal, par exemple 14.5 = 14h30.', default=9.0)
    end_hour = fields.Float(string='Heure de fin', help='Heure au format décimal, par exemple 16.0 = 16h00.', default=10.0)
    people_count = fields.Integer(string='Nombre de personnes', default=1)
    start_at = fields.Datetime(string='Début', required=True)
    end_at = fields.Datetime(string='Fin', required=True)
    amount_total = fields.Monetary(string='Montant de la réservation', currency_field='currency_id', default=0.0)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    payment_ids = fields.One2many('amarna.subscription.payment', 'reservation_id', string='Paiements')
    payment_total = fields.Monetary(string='Total payé', currency_field='currency_id', compute='_compute_payment', store=True)
    payment_valid = fields.Boolean(string='Paiement valide', compute='_compute_payment', store=True)
    payment_required = fields.Boolean(string='Paiement requis pour l’accès', default=True)
    status = fields.Char(string='Statut brut', default='En attente')
    status_normalized = fields.Selection([
        ('pending', 'En attente'), ('confirmed', 'Confirmée'), ('checked_in', 'Arrivée'),
        ('cancelled', 'Annulée'), ('unknown', 'Inconnue'),
    ], compute='_compute_status_normalized', store=True, string='Statut')
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)

    @api.depends('mobile_activity_code')
    def _compute_activity_id(self):
        for rec in self:
            rec.activity_id = self.env['amarna.club.activity']._find_by_mobile_code(rec.mobile_activity_code) if rec.mobile_activity_code else False

    @api.depends('status')
    def _compute_status_normalized(self):
        for rec in self:
            value = (rec.status or '').lower()
            rec.status_normalized = ('checked_in' if 'check' in value or 'arriv' in value else
                'confirmed' if 'confirm' in value else 'pending' if 'attente' in value or 'pending' in value else
                'cancelled' if 'cancel' in value or 'annul' in value else 'unknown') if value else False

    @api.depends('payment_ids.amount', 'payment_ids.state', 'amount_total')
    def _compute_payment(self):
        for rec in self:
            rec.payment_total = sum(rec.payment_ids.filtered(lambda p: p.state == 'confirmed').mapped('amount'))
            rec.payment_valid = not rec.payment_required or rec.amount_total <= 0 or rec.payment_total >= rec.amount_total

    @api.onchange('reservation_date', 'start_hour', 'end_hour')
    def _onchange_reservation_slot(self):
        for rec in self:
            if rec.reservation_date:
                rec.start_at = rec._slot_to_datetime(rec.reservation_date, rec.start_hour)
                rec.end_at = rec._slot_to_datetime(rec.reservation_date, rec.end_hour)
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') in ('New', 'Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('amarna.club.reservation') or 'Nouveau'
            if vals.get('reservation_date') and vals.get('start_hour') is not None and not vals.get('start_at'):
                vals['start_at'] = self._slot_to_datetime(fields.Date.to_date(vals['reservation_date']), vals['start_hour'])
            if vals.get('reservation_date') and vals.get('end_hour') is not None and not vals.get('end_at'):
                vals['end_at'] = self._slot_to_datetime(fields.Date.to_date(vals['reservation_date']), vals['end_hour'])
            if vals.get('start_at') and not vals.get('reservation_date'):
                start = fields.Datetime.to_datetime(vals['start_at'])
                end = fields.Datetime.to_datetime(vals.get('end_at')) if vals.get('end_at') else start
                vals['reservation_date'] = start.date()
                vals['start_hour'] = start.hour + start.minute / 60.0
                vals['end_hour'] = end.hour + end.minute / 60.0
        return super().create(vals_list)

    @api.constrains('partner_id', 'rfid_card_id')
    def _check_card_member(self):
        for rec in self:
            if rec.rfid_card_id and rec.partner_id and rec.rfid_card_id.partner_id != rec.partner_id:
                raise ValidationError('La carte RFID doit être attribuée au même membre que la réservation.')
    def _slot_to_datetime(self, reservation_date, hour):
        hours = int(hour or 0)
        minutes = int(round(((hour or 0) - hours) * 60))
        return datetime.combine(reservation_date, time(hours, minutes))

    @api.constrains('start_at', 'end_at', 'reservation_date', 'start_hour', 'end_hour')
    def _check_slot(self):
        for rec in self:
            if rec.start_at >= rec.end_at:
                raise ValidationError('La fin de la réservation doit être postérieure au début.')
            if rec.reservation_date and rec.start_at.date() != rec.end_at.date():
                raise ValidationError('Une réservation doit rester sur une seule date.')
            if not 0 <= rec.start_hour < 24 or not 0 <= rec.end_hour < 24:
                raise ValidationError('Les heures doivent être comprises entre 00:00 et 24:00.')

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id and not self.client_name:
            self.client_name = self.partner_id.name

    @api.onchange('subscription_id')
    def _onchange_subscription_id(self):
        if self.subscription_id:
            self.partner_id = self.subscription_id.partner_id
            if not self.rfid_card_id:
                self.rfid_card_id = self.subscription_id.rfid_card_id

    def _sync_rfid_access(self):
        Access = self.env['amarna.rfid.access']
        for reservation in self:
            paid = reservation.payment_valid
            card = reservation.rfid_card_id
            existing = Access.search([('reservation_id', '=', reservation.id)])
            if not paid or not card or reservation.status_normalized == 'cancelled':
                existing.filtered(lambda a: a.state not in ('expired', 'cancelled')).write({'state': 'cancelled', 'active': False})
                if card:
                    card._sync_access_state()
                continue
            values = {'card_id': card.id, 'start_datetime': reservation.start_at, 'end_datetime': reservation.end_at,
                      'source': 'reservation', 'state': 'scheduled', 'active': True}
            if existing:
                existing[0].write(values)
            else:
                Access.create(dict(values, reservation_id=reservation.id, name='Réservation %s' % reservation.name))
            card._sync_access_state()

    def write(self, vals):
        vals = dict(vals)
        slot_fields = {'reservation_date', 'start_hour', 'end_hour'}
        if set(vals) & slot_fields:
            reservation_date = fields.Date.to_date(vals.get('reservation_date')) if vals.get('reservation_date') else self.reservation_date
            start_hour = vals.get('start_hour', self.start_hour)
            end_hour = vals.get('end_hour', self.end_hour)
            if reservation_date and start_hour is not None and end_hour is not None:
                vals['start_at'] = self._slot_to_datetime(reservation_date, start_hour)
                vals['end_at'] = self._slot_to_datetime(reservation_date, end_hour)
        result = super().write(vals)
        if set(vals) & {'rfid_card_id', 'partner_id', 'start_at', 'end_at', 'amount_total', 'payment_required', 'status', 'reservation_date', 'start_hour', 'end_hour'}:
            self._sync_rfid_access()
        return result
    def action_confirm(self):
        self.write({'status': 'Confirme'})
        self._sync_rfid_access()

    def action_check_in(self):
        self.write({'status': 'checkedin'})
        for rec in self:
            if rec.activity_id:
                occupancy = rec.activity_id.current_occupancy + max(rec.people_count, 1)
                rec.activity_id.current_occupancy = min(occupancy, rec.activity_id.max_capacity) if rec.activity_id.max_capacity else occupancy

    def action_cancel(self):
        self.write({'status': 'Annule'})
        self._sync_rfid_access()





