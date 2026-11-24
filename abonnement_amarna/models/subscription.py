# -*- coding: utf-8 -*-
from datetime import datetime, time, timedelta

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.exceptions import UserError, ValidationError


class AmarnaSubscription(models.Model):
    """Abonnement d'un membre à une formule.

    Lifecycle: draft -> confirmed -> (renewed each period) -> cancelled.
    Billing (invoices, payments, taxes) lives in the shared billing mixin.
    The displayed status (active / unpaid / expired) is derived, never stored.
    """
    _name = 'amarna.subscription'
    _description = 'Abonnement client'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'amarna.billing.mixin']
    _order = 'start_date desc, id desc'
    _billing_link_field = 'amarna_subscription_id'

    name = fields.Char(string='Référence', default='Nouveau', copy=False, readonly=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Membre', required=True, index=True, tracking=True)
    plan_id = fields.Many2one('amarna.subscription.plan', string='Formule', required=True, tracking=True)
    activity_id = fields.Many2one(
        'amarna.club.activity', string='Activité', related='plan_id.activity_id',
        store=True, readonly=True, index=True)
    user_id = fields.Many2one(
        'res.users', string='Responsable', default=lambda self: self.env.user, tracking=True)
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('cancelled', 'Annulé'),
    ], string='État', default='draft', required=True, tracking=True)
    subscription_status = fields.Selection([
        ('draft', 'Brouillon'),
        ('active', 'Actif'),
        ('unpaid', 'Impayé'),
        ('frozen', 'Suspendu'),
        ('expired', 'Expiré'),
        ('cancelled', 'Annulé'),
    ], string='Statut', compute='_compute_subscription_status',
        search='_search_subscription_status')

    start_date = fields.Date(string='Date de début', required=True, default=fields.Date.context_today, tracking=True)
    expiration_date = fields.Date(
        string='Date de fin', compute='_compute_expiration_date', store=True, readonly=False, tracking=True,
        help="Calculée depuis la durée de la formule. Modifiable pour une prolongation exceptionnelle.")
    billing_period_start = fields.Date(related='start_date', store=True, readonly=True, string='Début de la période facturée')
    auto_renew = fields.Boolean(string='Renouvellement automatique', tracking=True)
    freeze_start = fields.Date(string='Suspendu du', copy=False, tracking=True)
    freeze_end = fields.Date(string="Suspendu jusqu'au", copy=False, tracking=True)
    is_frozen = fields.Boolean(
        string='Suspendu', compute='_compute_is_frozen',
        help="L'abonnement est suspendu aujourd'hui (voyage, blessure...) : pas d'accès, "
             "et la date de fin a été repoussée d'autant.")
    close_reason_id = fields.Many2one(
        'amarna.subscription.close.reason', string="Motif d'arrêt", tracking=True)
    is_unlimited = fields.Boolean(string='Illimitée', compute='_compute_is_unlimited')
    sessions_label = fields.Char(
        string='Séances', compute='_compute_sessions_label',
        help="Séances restantes, ou « Illimité » pour une formule sans limite.")
    remaining_sessions = fields.Integer(string='Séances restantes')

    rfid_card_id = fields.Many2one('amarna.rfid.card', string='Carte RFID', tracking=True)
    expiry_notified = fields.Boolean(copy=False)

    line_ids = fields.One2many('amarna.subscription.line', 'subscription_id', string='Lignes', copy=True)
    amount_untaxed = fields.Monetary(
        string='Montant HT', currency_field='currency_id', compute='_compute_amounts', store=True)
    amount_total = fields.Monetary(
        string='Montant TTC', currency_field='currency_id', compute='_compute_amounts', store=True)

    invoice_ids = fields.One2many('account.move', 'amarna_subscription_id', string='Factures', readonly=True)
    invoice_count = fields.Integer(compute='_compute_invoice_count')
    history_ids = fields.One2many('amarna.subscription.history', 'subscription_id', string='Historique', readonly=True)
    checkin_ids = fields.One2many('amarna.checkin', 'subscription_id', string='Passages RFID')
    checkin_count = fields.Integer(compute='_compute_checkin_count')
    note = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    # ---------------------------------------------------------- Compute

    @api.depends('start_date', 'plan_id.subscription_type_id.duration_value',
                 'plan_id.subscription_type_id.duration_unit')
    def _compute_expiration_date(self):
        for rec in self:
            ptype = rec.plan_id.subscription_type_id
            rec.expiration_date = ptype._end_date(rec.start_date) if (ptype and rec.start_date) else False

    @api.depends('freeze_start', 'freeze_end')
    def _compute_is_frozen(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.is_frozen = bool(
                rec.freeze_start and rec.freeze_end
                and rec.freeze_start <= today <= rec.freeze_end)

    def _search_subscription_status(self, operator, value):
        """The status depends on today's date, so it is not stored: express
        each status with the stored fields it is computed from (same rules as
        `_compute_subscription_status`) and let the database filter."""
        # Odoo 20 normalises '=' to 'in' and hands the value over as an OrderedSet.
        if operator not in ('=', '!=', 'in', 'not in'):
            return NotImplemented
        if isinstance(value, (str, bool)) or value is None:
            wanted = {value}
        else:
            wanted = set(value)
        today = fields.Date.context_today(self)
        confirmed = [('state', '=', 'confirmed')]
        not_expired = ['|', ('expiration_date', '=', False), ('expiration_date', '>=', today)]
        frozen_now = [('freeze_start', '<=', today), ('freeze_end', '>=', today)]
        not_frozen = ['|', '|', ('freeze_start', '=', False),
                      ('freeze_start', '>', today), ('freeze_end', '<', today)]
        by_status = {
            'cancelled': [('state', '=', 'cancelled')],
            'draft': [('state', '=', 'draft')],
            'frozen': confirmed + frozen_now,
            'expired': confirmed + not_frozen + [('expiration_date', '<', today)],
            'unpaid': confirmed + not_frozen + not_expired + [('payment_valid', '=', False)],
            'active': confirmed + not_frozen + not_expired + [('payment_valid', '=', True)],
        }
        domain = Domain.OR(Domain(by_status[status]) for status in wanted if status in by_status)
        if not wanted & set(by_status):
            domain = Domain.FALSE
        return domain if operator in ('=', 'in') else ~domain

    @api.depends('remaining_sessions', 'plan_id.session_count')
    def _compute_sessions_label(self):
        for rec in self:
            rec.sessions_label = 'Illimité' if not rec.plan_id.session_count else str(rec.remaining_sessions)

    @api.depends('plan_id.session_count')
    def _compute_is_unlimited(self):
        for rec in self:
            rec.is_unlimited = not rec.plan_id.session_count

    @api.depends('state', 'expiration_date', 'payment_valid', 'freeze_start', 'freeze_end')
    def _compute_subscription_status(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.state == 'cancelled':
                rec.subscription_status = 'cancelled'
            elif rec.state == 'draft':
                rec.subscription_status = 'draft'
            elif rec.is_frozen:
                rec.subscription_status = 'frozen'
            elif rec.expiration_date and rec.expiration_date < today:
                rec.subscription_status = 'expired'
            elif not rec.payment_valid:
                rec.subscription_status = 'unpaid'
            else:
                rec.subscription_status = 'active'

    @api.depends('line_ids.product_uom_qty', 'line_ids.price_unit', 'line_ids.discount',
                 'line_ids.tax_ids', 'line_ids.display_type')
    def _compute_amounts(self):
        for rec in self:
            rec.amount_untaxed, rec.amount_total = rec._billing_amounts()

    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = len(rec.invoice_ids)

    def _compute_checkin_count(self):
        for rec in self:
            rec.checkin_count = len(rec.checkin_ids)

    def _billing_lines_vals(self):
        vals = []
        for line in self.line_ids.filtered(lambda l: l.product_id and not l.display_type):
            vals.append({
                'product': line.product_id,
                'name': line.name or line.product_id.display_name,
                'quantity': line.product_uom_qty,
                'price_unit': line.price_unit,
                'discount': line.discount,
                'tax_ids': line.tax_ids,
            })
        return vals

    # ---------------------------------------------------------- Onchange

    @api.onchange('plan_id')
    def _onchange_plan_id(self):
        for rec in self:
            if not rec.plan_id:
                continue
            rec.remaining_sessions = rec.plan_id.session_count
            rec.line_ids = [(5, 0, 0), (0, 0, rec.plan_id._billing_line_vals())]

    # ------------------------------------------------------- Constraints

    @api.constrains('rfid_card_id', 'partner_id')
    def _check_card_member(self):
        for rec in self:
            if rec.rfid_card_id and rec.rfid_card_id.partner_id and rec.rfid_card_id.partner_id != rec.partner_id:
                raise ValidationError('La carte RFID doit être attribuée au même membre que l’abonnement.')

    @api.constrains('partner_id', 'activity_id', 'state', 'expiration_date')
    def _check_one_active_subscription_per_activity(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.state != 'confirmed' or not rec.activity_id:
                continue
            duplicate = self.search_count([
                ('id', '!=', rec.id),
                ('partner_id', '=', rec.partner_id.id),
                ('activity_id', '=', rec.activity_id.id),
                ('state', '=', 'confirmed'),
                '|', ('expiration_date', '=', False), ('expiration_date', '>=', today),
            ])
            if duplicate:
                raise ValidationError(
                    'Ce membre possède déjà une formule active pour cette activité. '
                    'Il peut avoir plusieurs activités, mais une seule formule par activité.')

    # --------------------------------------------------------------- CRUD

    @api.model_create_multi
    def create(self, vals_list):
        Plan = self.env['amarna.subscription.plan']
        for vals in vals_list:
            if vals.get('name', 'Nouveau') in ('New', 'Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('amarna.subscription') or 'Nouveau'
            plan = Plan.browse(vals['plan_id']) if vals.get('plan_id') else Plan
            if plan:
                vals.setdefault('remaining_sessions', plan.session_count)
                if not vals.get('line_ids'):
                    vals['line_ids'] = [(0, 0, plan._billing_line_vals())]
        return super().create(vals_list)

    def write(self, vals):
        result = super().write(vals)
        if set(vals) & {'rfid_card_id', 'start_date', 'expiration_date', 'active', 'state', 'partner_id',
                        'freeze_start', 'freeze_end'}:
            self._sync_rfid_access()
        return result

    # ---------------------------------------------------------- RFID access

    def _access_window(self):
        start = datetime.combine(self.start_date, time.min)
        end = datetime.combine(self.expiration_date, time.max)
        return start, end

    def _sync_rfid_access(self):
        """Keep the RFID authorisation in step with the subscription state.

        An authorisation exists only while the subscription is confirmed,
        active, not expired, and the current period is paid.
        """
        Access = self.env['amarna.rfid.access']
        today = fields.Date.context_today(self)
        for sub in self:
            existing = Access.search([('subscription_id', '=', sub.id)])
            granted = (
                sub.state == 'confirmed' and sub.active and sub.payment_valid and not sub.is_frozen
                and sub.rfid_card_id and sub.start_date and sub.expiration_date
                and sub.expiration_date >= max(sub.start_date, today)
            )
            if not granted:
                existing.filtered(lambda a: a.state not in ('expired', 'cancelled')).write(
                    {'state': 'cancelled', 'active': False})
                if sub.rfid_card_id:
                    sub.rfid_card_id._sync_access_state()
                continue
            start, end = sub._access_window()
            values = {'card_id': sub.rfid_card_id.id, 'start_datetime': start, 'end_datetime': end,
                      'source': 'subscription', 'state': 'scheduled', 'active': True}
            if existing:
                existing[0].write(values)
            else:
                Access.create(dict(values, subscription_id=sub.id, name='Abonnement %s' % sub.name))
            sub.rfid_card_id._sync_access_state()

    # ------------------------------------------------------------ Actions

    def _create_history(self, reason):
        for rec in self:
            if rec.start_date and rec.expiration_date:
                self.env['amarna.subscription.history'].create({
                    'subscription_id': rec.id, 'plan_id': rec.plan_id.id,
                    'start_date': rec.start_date, 'expiration_date': rec.expiration_date,
                    'amount': rec.amount_total, 'reason': reason,
                })

    def action_confirm(self):
        for rec in self:
            if rec.state == 'confirmed':
                continue
            if not rec.plan_id or not rec.line_ids:
                raise UserError("Choisissez une formule avant de confirmer l'abonnement.")
            rec.write({'state': 'confirmed'})
            rec._create_history('initial')
        return True

    def action_draft(self):
        self.write({'state': 'draft'})
        return True

    def action_cancel(self):
        self.write({'state': 'cancelled'})
        return True

    def action_renew(self):
        """Start the next period right after the current one.

        The renewal is invoiced immediately (unless the period is free). Access
        stays closed until that invoice is paid.
        """
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError("Seul un abonnement confirmé peut être renouvelé.")
            start = (rec.expiration_date or fields.Date.context_today(rec)) + timedelta(days=1)
            rec.write({
                'start_date': start,
                'remaining_sessions': rec.plan_id.session_count,
                'expiry_notified': False,
            })
            rec._create_history('renewal')
            if rec.amount_total > 0:
                rec.action_create_invoice()
        return True

    def action_freeze(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': "Suspendre l'abonnement",
            'res_model': 'amarna.subscription.freeze', 'view_mode': 'form', 'target': 'new',
            'context': {'default_subscription_id': self.id}}

    def action_unfreeze(self):
        """Resume today: the unused frozen days come off the new end date."""
        today = fields.Date.context_today(self)
        for rec in self.filtered('is_frozen'):
            unused = (rec.freeze_end - today).days + 1
            rec.write({
                'freeze_end': today - timedelta(days=1),
                'expiration_date': rec.expiration_date - timedelta(days=unused)})
            rec.message_post(body="Abonnement repris le %s." % today, subtype_xmlid='mail.mt_note')
        return True

    def action_send_reminder(self):
        """Renewal reminder e-mail to the member."""
        template = self.env.ref('abonnement_amarna.mail_template_subscription_reminder')
        for rec in self:
            if not rec.partner_id.email:
                raise UserError("%s n'a pas d'adresse e-mail." % rec.partner_id.name)
            template.send_mail(rec.id, force_send=False)
            rec.message_post(body="Rappel de renouvellement envoyé à %s." % rec.partner_id.email,
                             subtype_xmlid='mail.mt_note')
        return True

    def action_view_checkins(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Passages RFID',
            'res_model': 'amarna.checkin',
            'view_mode': 'list,form',
            'domain': [('subscription_id', '=', self.id)],
            'context': {'default_subscription_id': self.id, 'default_partner_id': self.partner_id.id},
        }

    # --------------------------------------------------------------- Cron

    @api.model
    def cron_close_expired(self):
        """Daily: revoke access of expired subscriptions and alert the owner once."""
        today = fields.Date.context_today(self)
        expired = self.search([
            ('state', '=', 'confirmed'),
            ('expiration_date', '<', today),
        ])
        for sub in expired.filtered(lambda s: not s.expiry_notified):
            sub.message_post(
                body="<b>Abonnement arrivé à échéance</b> le %s. L'accès RFID est désactivé." % sub.expiration_date,
                subtype_xmlid='mail.mt_note')
            sub.expiry_notified = True
            if sub.user_id:
                sub.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary='Relancer le membre : abonnement %s expiré' % sub.name,
                    user_id=sub.user_id.id)
        expired._sync_rfid_access()
        # A suspension starts or ends on a given day: refresh the card access.
        self.search([('freeze_end', '!=', False), ('state', '=', 'confirmed')])._sync_rfid_access()
        self.env['amarna.rfid.access'].cron_sync_access()
        return True

    @api.model
    def cron_auto_renew(self):
        """Daily: renew and invoice subscriptions flagged for automatic renewal."""
        today = fields.Date.context_today(self)
        due = self.search([
            ('auto_renew', '=', True),
            ('state', '=', 'confirmed'),
            ('expiration_date', '<', today),
        ])
        for sub in due:
            # A previous period still waiting for payment blocks the renewal.
            if sub.billing_state in ('unpaid', 'partial'):
                sub.message_post(
                    body="Renouvellement reporté : la période précédente n'est pas encore payée.",
                    subtype_xmlid='mail.mt_note')
                continue
            sub.action_renew()
            sub.message_post(
                body="Renouvellement automatique effectué pour la période du %s au %s." % (
                    sub.start_date, sub.expiration_date),
                subtype_xmlid='mail.mt_note')
        return True
