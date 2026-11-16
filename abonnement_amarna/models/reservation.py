# -*- coding: utf-8 -*-
from datetime import datetime, time

import pytz

from odoo import api, fields, models
from odoo.exceptions import ValidationError

# Canonical values written by the tablet and by the Odoo buttons. The status
# is a free Char on purpose (existing rows hold French labels as well); the
# normalized selection below maps both to one of five states.
STATUS_PENDING = 'pending'
STATUS_CONFIRMED = 'confirmed'
STATUS_CHECKED_IN = 'checkedin'
STATUS_CANCELLED = 'cancelled'

SLOT_FIELDS = {'reservation_date', 'start_hour', 'end_hour'}
DATETIME_FIELDS = {'start_at', 'end_at'}


class AmarnaClubReservation(models.Model):
    _name = 'amarna.club.reservation'
    _description = 'Réservation ponctuelle du club'
    _order = 'start_at desc'

    name = fields.Char(string='Référence / titre', required=True)
    mobile_activity_code = fields.Char(string='Code activité mobile')
    activity_id = fields.Many2one('amarna.club.activity', string='Activité', compute='_compute_activity_id', store=True, readonly=False)
    client_name = fields.Char(string='Nom du client')
    partner_id = fields.Many2one('res.partner', string='Membre / client')
    subscription_id = fields.Many2one('amarna.subscription', string='Abonnement utilisé')
    rfid_card_id = fields.Many2one('amarna.rfid.card', string='Carte RFID', ondelete='set null')
    reservation_date = fields.Date(string='Date de réservation (locale)', default=fields.Date.context_today)
    start_hour = fields.Float(string='Heure de début (locale)', help='Heure au format décimal, par exemple 14.5 = 14h30.', default=9.0)
    end_hour = fields.Float(string='Heure de fin (locale)', help='Heure au format décimal, par exemple 16.0 = 16h00.', default=10.0)
    people_count = fields.Integer(string='Nombre de personnes', default=1)
    # start_at / end_at are naive UTC, as every Odoo Datetime field.
    start_at = fields.Datetime(string='Début (UTC)', required=True)
    end_at = fields.Datetime(string='Fin (UTC)', required=True)
    amount_total = fields.Monetary(string='Montant de la réservation', currency_field='currency_id', default=0.0)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    payment_ids = fields.One2many('amarna.subscription.payment', 'reservation_id', string='Paiements')
    payment_total = fields.Monetary(string='Total payé', currency_field='currency_id', compute='_compute_payment', store=True)
    payment_valid = fields.Boolean(string='Paiement valide', compute='_compute_payment', store=True)
    payment_required = fields.Boolean(string='Paiement requis pour l’accès', default=True)
    status = fields.Char(string='Statut (valeur brute)', default=STATUS_PENDING)
    status_normalized = fields.Selection([
        ('pending', 'En attente'), ('confirmed', 'Confirmée'), ('checked_in', 'Arrivée'),
        ('cancelled', 'Annulée'), ('unknown', 'Inconnue'),
    ], compute='_compute_status_normalized', store=True, string='Statut')
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)

    # ------------------------------------------------------------ Computes

    @api.depends('mobile_activity_code')
    def _compute_activity_id(self):
        Activity = self.env['amarna.club.activity']
        for rec in self:
            if rec.mobile_activity_code:
                rec.activity_id = Activity._find_by_mobile_code(rec.mobile_activity_code)
            elif not rec.activity_id:
                rec.activity_id = False

    @api.depends('status')
    def _compute_status_normalized(self):
        for rec in self:
            value = (rec.status or '').lower()
            if not value:
                rec.status_normalized = False
            elif 'check' in value or 'arriv' in value:
                rec.status_normalized = 'checked_in'
            elif 'confirm' in value:
                rec.status_normalized = 'confirmed'
            elif 'attente' in value or 'pending' in value:
                rec.status_normalized = 'pending'
            elif 'cancel' in value or 'annul' in value:
                rec.status_normalized = 'cancelled'
            else:
                rec.status_normalized = 'unknown'

    @api.depends('payment_ids.amount', 'payment_ids.state', 'amount_total', 'payment_required')
    def _compute_payment(self):
        for rec in self:
            rec.payment_total = sum(rec.payment_ids.filtered(lambda p: p.state == 'confirmed').mapped('amount'))
            rec.payment_valid = not rec.payment_required or rec.amount_total <= 0 or rec.payment_total >= rec.amount_total

    # ------------------------------------------------------- Time handling

    def _local_tz(self):
        """Club time zone: the acting user's, then the company's, then UTC."""
        name = self.env.user.tz or self.env.company.partner_id.tz or 'UTC'
        try:
            return pytz.timezone(name)
        except pytz.UnknownTimeZoneError:
            return pytz.UTC

    def _local_to_utc(self, day, hour):
        """Naive UTC datetime for a decimal local hour on a local calendar day."""
        if hour is None or not 0 <= hour < 24:
            raise ValidationError('Les heures doivent être comprises entre 00:00 et 24:00.')
        hours = int(hour)
        minutes = int(round((hour - hours) * 60))
        if minutes == 60:
            hours, minutes = hours + 1, 0
        local = self._local_tz().localize(datetime.combine(day, time(min(hours, 23), minutes)))
        return local.astimezone(pytz.UTC).replace(tzinfo=None)

    def _utc_to_local(self, value):
        """(local date, decimal local hour) for a naive UTC datetime."""
        local = pytz.UTC.localize(value).astimezone(self._local_tz())
        return local.date(), local.hour + local.minute / 60.0

    def _slot_datetimes(self, day, start_hour, end_hour):
        return self._local_to_utc(day, start_hour), self._local_to_utc(day, end_hour)

    @api.onchange('reservation_date', 'start_hour', 'end_hour')
    def _onchange_reservation_slot(self):
        for rec in self:
            if rec.reservation_date and rec.start_hour is not None and rec.end_hour is not None:
                try:
                    rec.start_at, rec.end_at = rec._slot_datetimes(
                        rec.reservation_date, rec.start_hour, rec.end_hour)
                except ValidationError:
                    pass

    # ----------------------------------------------------------- CRUD

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('start_at') and vals.get('end_at'):
                # Datetimes win (tablet payloads are UTC); derive the local slot.
                start = fields.Datetime.to_datetime(vals['start_at'])
                end = fields.Datetime.to_datetime(vals['end_at'])
                day, start_hour = self._utc_to_local(start)
                _day, end_hour = self._utc_to_local(end)
                vals.update(reservation_date=day, start_hour=start_hour, end_hour=end_hour)
            else:
                day = fields.Date.to_date(vals.get('reservation_date')) or fields.Date.context_today(self)
                vals['start_at'], vals['end_at'] = self._slot_datetimes(
                    day, vals.get('start_hour', 9.0), vals.get('end_hour', 10.0))
                vals.setdefault('reservation_date', day)
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)
        changes_slot = bool(set(vals) & SLOT_FIELDS)
        changes_datetime = bool(set(vals) & DATETIME_FIELDS)

        if len(self) > 1 and (changes_slot or changes_datetime):
            # Each record has its own slot: write them one by one.
            for rec in self:
                rec.write(dict(vals))
            return True

        if len(self) == 1:
            if changes_slot and not changes_datetime:
                day = fields.Date.to_date(vals.get('reservation_date', self.reservation_date))
                vals['start_at'], vals['end_at'] = self._slot_datetimes(
                    day,
                    vals.get('start_hour', self.start_hour),
                    vals.get('end_hour', self.end_hour),
                )
            elif changes_datetime:
                start = fields.Datetime.to_datetime(vals.get('start_at', self.start_at))
                end = fields.Datetime.to_datetime(vals.get('end_at', self.end_at))
                day, start_hour = self._utc_to_local(start)
                _day, end_hour = self._utc_to_local(end)
                vals.update(reservation_date=day, start_hour=start_hour, end_hour=end_hour)

        old_statuses = {rec.id: rec.status_normalized for rec in self}
        result = super().write(vals)

        if set(vals) & {'rfid_card_id', 'partner_id', 'start_at', 'end_at', 'amount_total',
                        'payment_required', 'status'}:
            self._sync_rfid_access()

        # Check-in is processed once, on the transition into "checked in",
        # whichever way the status was changed (button, tablet, API).
        for rec in self:
            if old_statuses.get(rec.id) != 'checked_in' and rec.status_normalized == 'checked_in':
                rec._process_check_in()
        return result

    # ------------------------------------------------------- Constraints

    @api.constrains('activity_id', 'start_at', 'end_at')
    def _check_activity_availability(self):
        """Reject slots outside the activity's open/closure window."""
        for rec in self:
            if rec.status_normalized == 'cancelled':
                continue
            if not rec.activity_id:
                raise ValidationError('Sélectionnez une activité valide pour la réservation.')
            if rec.activity_id.is_available_at(rec.start_at, rec.end_at):
                continue
            activity = rec.activity_id
            if activity.mobile_status not in ('open', 'warning'):
                raise ValidationError(
                    "La réservation est impossible : l'activité « %s » n'est pas ouverte (statut : %s)." % (
                        activity.name,
                        dict(activity._fields['mobile_status'].selection).get(activity.mobile_status),
                    ))
            if activity.closure_start:
                raise ValidationError(
                    "La réservation est impossible : l'activité « %s » est fermée à partir du %s (UTC)%s." % (
                        activity.name, activity.closure_start,
                        (' jusqu’au %s (UTC)' % activity.closure_end) if activity.closure_end else '',
                    ))
            raise ValidationError(
                "Le créneau demandé n'est pas disponible pour l'activité « %s »." % activity.name)

    @api.constrains('start_at', 'end_at')
    def _check_slot(self):
        for rec in self:
            if rec.start_at >= rec.end_at:
                raise ValidationError('La fin de la réservation doit être postérieure au début.')
            if rec._utc_to_local(rec.start_at)[0] != rec._utc_to_local(rec.end_at)[0]:
                raise ValidationError('Une réservation doit rester sur une seule date.')

    @api.constrains('partner_id', 'rfid_card_id')
    def _check_card_member(self):
        for rec in self:
            if rec.rfid_card_id and rec.partner_id and rec.rfid_card_id.partner_id != rec.partner_id:
                raise ValidationError('La carte RFID doit être attribuée au même membre que la réservation.')

    # ---------------------------------------------------------- Onchanges

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

    # ------------------------------------------------------ Business logic

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

    def _process_check_in(self):
        self.ensure_one()
        if self.subscription_id:
            sub = self.subscription_id
            if not sub.active or sub.subscription_status in ('closed', 'cancel'):
                raise ValidationError("L'abonnement %s du membre n'est pas actif ou est clos." % sub.name)
            if sub.expiration_date and sub.expiration_date < fields.Date.context_today(self):
                raise ValidationError("L'abonnement %s du membre est expiré depuis le %s." % (sub.name, sub.expiration_date))
            if sub.plan_id and sub.plan_id.session_count > 0:
                needed = max(self.people_count, 1)
                if sub.remaining_sessions < needed:
                    raise ValidationError(
                        "Solde de séances insuffisant sur l'abonnement %s (%s restante(s), %s requise(s))." % (
                            sub.name, sub.remaining_sessions, needed))
                sub.remaining_sessions -= needed
                sub.message_post(
                    body="<b>[CHECK-IN] Séance décomptée :</b> Check-in effectué pour la réservation <b>%s</b>. Séances restantes : <b>%s</b>." % (self.name, sub.remaining_sessions),
                    subtype_xmlid="mail.mt_note"
                )
                if sub.remaining_sessions == 0:
                    sub.message_post(
                        body="<b>[ALERTE]</b> Le forfait de séances de cet abonnement est désormais totalement épuisé !",
                        subtype_xmlid="mail.mt_comment"
                    )
                    if sub.partner_id:
                        sub.partner_id.message_post(
                            body="<b>[ALERTE]</b> L'abonnement <b>%s</b> de %s n'a plus de séances disponibles." % (sub.name, sub.partner_id.name),
                            subtype_xmlid="mail.mt_comment"
                        )
        if self.activity_id:
            occupancy = self.activity_id.current_occupancy + max(self.people_count, 1)
            capacity = self.activity_id.max_capacity
            self.activity_id.current_occupancy = min(occupancy, capacity) if capacity else occupancy

    # ------------------------------------------------------------ Buttons

    def action_confirm(self):
        self.write({'status': STATUS_CONFIRMED})

    def action_check_in(self):
        # The status write triggers _process_check_in exactly once (see write).
        self.write({'status': STATUS_CHECKED_IN})

    def action_cancel(self):
        self.write({'status': STATUS_CANCELLED})
