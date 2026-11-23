# -*- coding: utf-8 -*-
from datetime import datetime, time

import pytz

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.misc import format_amount

# Canonical status tokens. The tablet sends the same tokens (see
# OdooReservationService.statusToken in the Flutter app).
STATUS_PENDING = 'pending'
STATUS_CONFIRMED = 'confirmed'
STATUS_CHECKED_IN = 'checkedin'
STATUS_CANCELLED = 'cancelled'

SLOT_FIELDS = {'reservation_date', 'start_hour', 'end_hour'}
DATETIME_FIELDS = {'start_at', 'end_at'}


class AmarnaClubReservation(models.Model):
    """Réservation ponctuelle d'une activité (créneau, personnes, tarif).

    A reservation can be paid at the desk (invoice + payment through Odoo
    accounting) or covered by a subscription (then it costs nothing and checks
    in against the subscription's sessions).
    """
    _name = 'amarna.club.reservation'
    _inherit = ['mail.thread', 'amarna.billing.mixin', 'amarna.activity.mixin']
    _description = 'Réservation du club'
    _order = 'start_at desc'
    _billing_link_field = 'amarna_reservation_id'

    name = fields.Char(string='Référence', required=True, copy=False)
    client_name = fields.Char(string='Nom du client')
    partner_id = fields.Many2one('res.partner', string='Membre / client', index=True)
    subscription_id = fields.Many2one(
        'amarna.subscription', string='Abonnement utilisé',
        domain="[('partner_id', '=', partner_id), ('state', '=', 'confirmed')]")
    rfid_card_id = fields.Many2one('amarna.rfid.card', string='Carte RFID', ondelete='set null')
    reservation_date = fields.Date(string='Date (locale)', default=fields.Date.context_today, required=True)
    billing_period_start = fields.Date(related='reservation_date', store=True, readonly=True, string='Date facturée')
    start_hour = fields.Float(
        string='Heure de début (locale)',
        default=lambda self: self.env.company.amarna_default_start_hour,
        help='Heure décimale : 14.5 = 14h30.')
    end_hour = fields.Float(
        string='Heure de fin (locale)',
        default=lambda self: self.env.company.amarna_default_end_hour,
        help='Heure décimale : 16.0 = 16h00.')
    people_count = fields.Integer(string='Nombre de personnes', default=1)
    # start_at / end_at are naive UTC, as every Odoo Datetime field.
    # Stored in UTC; Odoo shows Datetime fields in the user's timezone.
    start_at = fields.Datetime(string='Début', required=True, index=True)
    end_at = fields.Datetime(string='Fin', required=True)

    status = fields.Selection([
        (STATUS_PENDING, 'En attente'),
        (STATUS_CONFIRMED, 'Confirmée'),
        (STATUS_CHECKED_IN, 'Arrivée'),
        (STATUS_CANCELLED, 'Annulée'),
    ], string='Statut', default=STATUS_PENDING, required=True, tracking=True)

    amount_untaxed = fields.Monetary(
        string='Montant HT', currency_field='currency_id', store=True, readonly=False,
        compute='_compute_amount_untaxed',
        help="Par défaut : tarif de l'activité × nombre de personnes. Zéro si "
             "la réservation est couverte par un abonnement.")
    amount_total = fields.Monetary(
        string='Montant TTC', currency_field='currency_id', store=True,
        compute='_compute_amount_total')
    invoice_ids = fields.One2many('account.move', 'amarna_reservation_id', string='Factures', readonly=True)
    invoice_count = fields.Integer(compute='_compute_invoice_count')

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    # ------------------------------------------------------------ Compute

    @api.depends('activity_id.unit_price', 'people_count', 'subscription_id')
    def _compute_amount_untaxed(self):
        for rec in self:
            if rec.subscription_id:
                rec.amount_untaxed = 0.0
            else:
                rec.amount_untaxed = (rec.activity_id.unit_price or 0.0) * max(rec.people_count, 1)

    @api.depends('amount_untaxed', 'activity_id', 'status')
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = rec._billing_amounts()[1]

    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = len(rec.invoice_ids)

    def _billing_ensure_partner(self):
        # Walk-in clients often have no contact yet: create one from the name.
        if not self.partner_id:
            self.partner_id = self.env['res.partner'].create({
                'name': self.client_name or self.name,
            })

    def _billing_lines_vals(self):
        self.ensure_one()
        if not self.activity_id or self.amount_untaxed <= 0:
            return []
        # A cancelled booking that was never invoiced owes nothing.
        if self.status == STATUS_CANCELLED and not self.invoice_ids:
            return []
        product = self.activity_id._get_billing_product()
        # Bookings made on the tablet are already named "Activité – Client".
        label = self.name if self.activity_id.name in (self.name or '') else '%s – %s' % (self.activity_id.name, self.name)
        return [{
            'product': product,
            'name': label,
            'quantity': 1.0,
            'price_unit': self.amount_untaxed,
            'discount': 0.0,
            'tax_ids': self.activity_id.tax_ids,
        }]

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

    # --------------------------------------------------------------- CRUD

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
            if not vals.get('name'):
                activity = self.env['amarna.club.activity'].browse(vals.get('activity_id'))
                vals['name'] = ' - '.join(filter(None, [
                    activity.name if activity else vals.get('mobile_activity_code'),
                    vals.get('client_name'),
                ])) or 'Réservation'
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)
        changes_slot = bool(set(vals) & SLOT_FIELDS)
        changes_datetime = bool(set(vals) & DATETIME_FIELDS)

        if len(self) > 1 and (changes_slot or changes_datetime):
            for rec in self:
                rec.write(dict(vals))
            return True

        if len(self) == 1:
            if changes_slot and not changes_datetime:
                day = fields.Date.to_date(vals.get('reservation_date', self.reservation_date))
                vals['start_at'], vals['end_at'] = self._slot_datetimes(
                    day, vals.get('start_hour', self.start_hour), vals.get('end_hour', self.end_hour))
            elif changes_datetime:
                start = fields.Datetime.to_datetime(vals.get('start_at', self.start_at))
                end = fields.Datetime.to_datetime(vals.get('end_at', self.end_at))
                day, start_hour = self._utc_to_local(start)
                _day, end_hour = self._utc_to_local(end)
                vals.update(reservation_date=day, start_hour=start_hour, end_hour=end_hour)

        old_statuses = {rec.id: rec.status for rec in self}
        result = super().write(vals)

        if set(vals) & {'rfid_card_id', 'partner_id', 'start_at', 'end_at', 'amount_untaxed',
                        'payment_required', 'status', 'subscription_id', 'reservation_date'}:
            self._sync_rfid_access()

        # Check-in is processed once, on the transition into "checked in",
        # whichever way the status was changed (button, tablet, API).
        for rec in self:
            if old_statuses.get(rec.id) != STATUS_CHECKED_IN and rec.status == STATUS_CHECKED_IN:
                rec._process_check_in()
        return result

    # ------------------------------------------------------- Constraints

    @api.constrains('activity_id', 'start_at', 'end_at', 'status')
    def _check_activity_availability(self):
        """Reject slots outside the activity's open/closure window."""
        for rec in self:
            if rec.status == STATUS_CANCELLED:
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

    @api.constrains('people_count')
    def _check_people_count(self):
        for rec in self:
            if rec.people_count < 1:
                raise ValidationError('Une réservation doit compter au moins une personne.')

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
            existing = Access.search([('reservation_id', '=', reservation.id)])
            card = reservation.rfid_card_id
            granted = (
                reservation.payment_valid and card
                and reservation.status != STATUS_CANCELLED
            )
            if not granted:
                existing.filtered(lambda a: a.state not in ('expired', 'cancelled')).write(
                    {'state': 'cancelled', 'active': False})
                if card:
                    card._sync_access_state()
                continue
            values = {'card_id': card.id, 'start_datetime': reservation.start_at,
                      'end_datetime': reservation.end_at, 'source': 'reservation',
                      'state': 'scheduled', 'active': True}
            if existing:
                existing[0].write(values)
            else:
                Access.create(dict(values, reservation_id=reservation.id,
                                   name='Réservation %s' % reservation.name))
            card._sync_access_state()

    def _process_check_in(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        if not self.payment_valid:
            raise ValidationError(
                "Arrivée refusée : la réservation n'est pas payée (reste à payer : %s)." % format_amount(
                    self.env, self.amount_total - self.amount_paid, self.currency_id))

        if self.subscription_id:
            sub = self.subscription_id
            if sub.state != 'confirmed' or not sub.active:
                raise ValidationError("L'abonnement %s du membre n'est pas actif." % sub.name)
            if sub.expiration_date and sub.expiration_date < today:
                raise ValidationError("L'abonnement %s du membre est expiré depuis le %s." % (
                    sub.name, sub.expiration_date))
            if not sub.payment_valid:
                raise ValidationError("L'abonnement %s n'est pas payé pour la période en cours." % sub.name)
            if not sub.is_unlimited:
                needed = max(self.people_count, 1)
                if sub.remaining_sessions < needed:
                    raise ValidationError(
                        "Solde de séances insuffisant sur l'abonnement %s (%s restante(s), %s requise(s))." % (
                            sub.name, sub.remaining_sessions, needed))
                sub.remaining_sessions -= needed
                sub.message_post(
                    body="<b>Check-in :</b> %s séance(s) décomptée(s) pour la réservation <b>%s</b>. "
                         "Séances restantes : <b>%s</b>." % (needed, self.name, sub.remaining_sessions),
                    subtype_xmlid='mail.mt_note')
                if sub.remaining_sessions == 0:
                    sub.message_post(
                        body="<b>Alerte :</b> le forfait de séances de cet abonnement est épuisé.",
                        subtype_xmlid='mail.mt_comment')

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
