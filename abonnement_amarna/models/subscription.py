# -*- coding: utf-8 -*-
from datetime import datetime, time, timedelta
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AmarnaSubscription(models.Model):
    _name = 'amarna.subscription'
    _description = 'Abonnement client'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'start_date desc, id desc'

    name = fields.Char(string='Référence', default='Nouveau', copy=False, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Membre / client', required=True, tracking=True)
    plan_id = fields.Many2one('amarna.subscription.plan', string='Formule d’abonnement', tracking=True)
    recurring_plan_id = fields.Many2one('amarna.recurring.plan', string='Plan récurrent', tracking=True)
    activity_id = fields.Many2one('amarna.club.activity', string='Activité')
    auto_renew = fields.Boolean(string='Renouvellement automatique', default=False, tracking=True)
    start_date = fields.Date(string='Date de début', default=fields.Date.today, required=True)
    expiration_date = fields.Date(string='Date de fin', tracking=True)
    order_date = fields.Datetime(string='Date de commande', default=fields.Datetime.now)
    next_invoice_date = fields.Date(string='Prochaine facture')
    delivery_date = fields.Date(string='Date de livraison')
    until_date = fields.Date(string='Jusqu’au')
    payment_term_id = fields.Many2one('account.payment.term', string='Conditions de paiement')
    remaining_sessions = fields.Integer(string='Séances restantes')
    active = fields.Boolean(string='Abonnement actif', default=True, tracking=True)
    rfid_card_id = fields.Many2one('amarna.rfid.card', string='Carte RFID')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', store=True, readonly=True)
    line_ids = fields.One2many('amarna.subscription.line', 'subscription_id', string='Lignes')
    payment_ids = fields.One2many('amarna.subscription.payment', 'subscription_id', string='Paiements')
    history_ids = fields.One2many('amarna.subscription.history', 'subscription_id', string='Historique', readonly=True)
    amount_untaxed = fields.Monetary(string='Montant', currency_field='currency_id', compute='_compute_amounts', store=True)
    amount_total = fields.Monetary(string='Total', currency_field='currency_id', compute='_compute_amounts', store=True)
    payment_total = fields.Monetary(string='Total payé', currency_field='currency_id', compute='_compute_payment', store=True)
    payment_valid = fields.Boolean(string='Paiement valide', compute='_compute_payment', store=True)
    payment_balance = fields.Monetary(string='Solde', currency_field='currency_id', compute='_compute_payment', store=True)
    invoice_id = fields.Many2one('account.move', string='Facture')
    invoice_count = fields.Integer(compute='_compute_invoice_count', string='Factures')
    sale_person_id = fields.Many2one('res.users', string='Commercial', default=lambda self: self.env.user)
    client_reference = fields.Char(string='Référence client')
    note = fields.Text(string='Notes')
    state = fields.Selection([
        ('draft', 'Brouillon'), ('sent', 'Envoyé'), ('sale', 'Confirmé'), ('cancel', 'Annulé'),
    ], string='État', default='draft', tracking=True)
    subscription_status = fields.Selection([
        ('draft', 'Brouillon'), ('running', 'En cours'), ('paid', 'Payé'), ('closed', 'Clos'), ('cancel', 'Annulé'),
    ], string='Statut', compute='_compute_subscription_status', store=True, tracking=True)
    invoice_state = fields.Selection(related='invoice_id.state', string='État facture', store=True)
    payment_state = fields.Selection(related='invoice_id.payment_state', string='État paiement', store=True)

    @api.depends('line_ids.price_subtotal')
    def _compute_amounts(self):
        for rec in self:
            rec.amount_untaxed = sum(rec.line_ids.mapped('price_subtotal'))
            rec.amount_total = rec.amount_untaxed

    @api.depends('payment_ids.amount', 'payment_ids.state', 'amount_total')
    def _compute_payment(self):
        for rec in self:
            rec.payment_total = sum(rec.payment_ids.filtered(lambda p: p.state == 'confirmed').mapped('amount'))
            rec.payment_valid = rec.amount_total <= 0 or rec.payment_total >= rec.amount_total
            rec.payment_balance = rec.amount_total - rec.payment_total

    @api.depends('state', 'payment_valid', 'expiration_date', 'active')
    def _compute_subscription_status(self):
        today = fields.Date.today()
        for rec in self:
            if rec.state == 'cancel':
                rec.subscription_status = 'cancel'
            elif rec.expiration_date and rec.expiration_date < today:
                rec.subscription_status = 'closed'
            elif rec.payment_valid:
                rec.subscription_status = 'paid' if rec.state in ('draft', 'sent') else 'running'
            elif rec.state == 'sale':
                rec.subscription_status = 'running'
            else:
                rec.subscription_status = 'draft'

    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = 1 if rec.invoice_id else 0

    @api.onchange('plan_id')
    def _onchange_plan_id(self):
        if self.plan_id:
            self.activity_id = self.plan_id.activity_id
            self.remaining_sessions = self.plan_id.session_count
            self.expiration_date = self.start_date + timedelta(days=self.plan_id.duration_days)

    @api.constrains('partner_id', 'rfid_card_id')
    def _check_card_member(self):
        for rec in self:
            if rec.rfid_card_id and rec.rfid_card_id.partner_id and rec.rfid_card_id.partner_id != rec.partner_id:
                raise ValidationError('La carte RFID doit être attribuée au même membre que l’abonnement.')
    def _access_window(self):
        start = datetime.combine(self.start_date, time.min)
        end = datetime.combine(self.expiration_date, time.max) if self.expiration_date else start + timedelta(days=1)
        return start, end

    def _sync_rfid_access(self):
        Access = self.env['amarna.rfid.access']
        for subscription in self:
            existing = Access.search([('subscription_id', '=', subscription.id)])
            if not subscription.payment_valid or not subscription.active or subscription.state == 'cancel' or not subscription.rfid_card_id or not subscription.expiration_date or subscription.expiration_date < subscription.start_date:
                existing.filtered(lambda a: a.state not in ('expired', 'cancelled')).write({'state': 'cancelled', 'active': False})
                if subscription.rfid_card_id:
                    subscription.rfid_card_id._sync_access_state()
                continue
            start, end = subscription._access_window()
            values = {'card_id': subscription.rfid_card_id.id, 'start_datetime': start, 'end_datetime': end,
                      'source': 'subscription', 'state': 'scheduled', 'active': True}
            if existing:
                existing[0].write(values)
            else:
                Access.create(dict(values, subscription_id=subscription.id, name='Abonnement %s' % subscription.name))
            subscription.rfid_card_id._sync_access_state()

    @api.model
    def cron_close_expired(self):
        expired = self.search([('expiration_date', '<', fields.Date.today()), ('active', '=', True)])
        for sub in expired:
            sub.write({'active': False})
            sub.message_post(
                body="<b>[ALERTE Expiration]</b> La date d'échéance (%s) est atteinte. L'abonnement et les accès RFID ont été désactivés." % sub.expiration_date,
                subtype_xmlid="mail.mt_comment"
            )
            if sub.sale_person_id:
                try:
                    activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
                    model_id = self.env['ir.model']._get_id('amarna.subscription')
                    if activity_type and model_id:
                        self.env['mail.activity'].create({
                            'activity_type_id': activity_type.id,
                            'summary': "Relancer client : Abonnement %s expiré" % sub.name,
                            'note': "L'abonnement %s de %s a expiré. Veuillez contacter le membre pour son renouvellement." % (sub.name, sub.partner_id.name if sub.partner_id else ''),
                            'res_model_id': model_id,
                            'res_id': sub.id,
                            'user_id': sub.sale_person_id.id,
                        })
                except Exception:
                    pass
        expired._sync_rfid_access()
        self.env['amarna.rfid.access'].cron_sync_access()
        return True

    @api.model
    def cron_auto_renew(self):
        today = fields.Date.today()
        to_renew = self.search([
            ('auto_renew', '=', True),
            ('active', '=', True),
            ('expiration_date', '<=', today),
            ('state', '=', 'sale'),
        ])
        for sub in to_renew:
            sub.action_renew()
            if not sub.invoice_id or sub.invoice_id.state == 'cancel':
                sub.action_create_invoice()
            sub.message_post(
                body="<b>[AUTO-RENEW]</b> L'abonnement a été automatiquement renouvelé et une facture a été générée.",
                subtype_xmlid="mail.mt_comment"
            )
        return True

    def _create_history(self, reason='initial'):
        for rec in self:
            if rec.plan_id and rec.start_date and rec.expiration_date:
                self.env['amarna.subscription.history'].create({
                    'subscription_id': rec.id, 'plan_id': rec.plan_id.id,
                    'start_date': rec.start_date, 'expiration_date': rec.expiration_date,
                    'amount': rec.amount_total, 'reason': reason,
                })

    def action_send(self):
        self.write({'state': 'sent'})

    def action_confirm(self):
        self.write({'state': 'sale'})
        self._create_history('initial')
        self._sync_rfid_access()

    def action_cancel(self):
        self.write({'state': 'cancel', 'active': False})
        self._sync_rfid_access()

    def action_draft(self):
        self.write({'state': 'draft'})
        self._sync_rfid_access()

    def action_renew(self):
        for rec in self:
            start = rec.expiration_date + timedelta(days=1) if rec.expiration_date else fields.Date.today()
            duration = rec.plan_id.duration_days if rec.plan_id else 0
            rec.write({'start_date': start, 'expiration_date': start + timedelta(days=duration), 'state': 'sale', 'active': True})
            rec._create_history('renewal')
            rec._sync_rfid_access()
        return True

    def action_deactivate(self):
        self.write({'active': False})
        self._sync_rfid_access()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') in ('New', 'Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('amarna.subscription') or 'Nouveau'
        return super().create(vals_list)

    def write(self, vals):
        old_cards = self.mapped('rfid_card_id') if 'rfid_card_id' in vals else self.env['amarna.rfid.card']
        result = super().write(vals)
        if not self.env.context.get('skip_rfid_sync') and set(vals) & {'rfid_card_id', 'start_date', 'expiration_date', 'active', 'state'}:
            self._sync_rfid_access()
            (old_cards - self.mapped('rfid_card_id'))._sync_access_state()
        return result

    def action_create_invoice(self):
        self.ensure_one()
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice', 'partner_id': self.partner_id.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': line.product_id.id, 'quantity': line.product_uom_qty,
                'price_unit': line.price_unit, 'name': line.name,
            }) for line in self.line_ids if line.product_id],
        })
        self.invoice_id = invoice.id
        return {'type': 'ir.actions.act_window', 'res_model': 'account.move', 'view_mode': 'form', 'res_id': invoice.id}

    def action_view_invoice(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': 'Facture', 'res_model': 'account.move', 'view_mode': 'form', 'res_id': self.invoice_id.id} if self.invoice_id else True

    def action_print_subscription(self):
        return True

    def action_preview_subscription(self):
        return True

    def action_discount(self):
        return True





