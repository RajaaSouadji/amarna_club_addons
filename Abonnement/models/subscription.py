from odoo import models, fields, api
from datetime import timedelta


class AmarnaSubscription(models.Model):
    _name = 'amarna.subscription'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Client Subscription'
    _rec_name = 'partner_id'

    # =====================================================
    # HEADER
    # =====================================================

    name = fields.Char(
        string='Reference',
        default='New',
        copy=False,
        tracking=True
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Client',
        required=True,
        tracking=True
    )

    recurring_plan_id = fields.Many2one(
        'amarna.recurring.plan',
        string='Plan récurrent',
        tracking=True
    )

    order_date = fields.Datetime(
        string="Date de la commande",
        default=fields.Datetime.now,
        tracking=True,
    )

    until_date = fields.Date(
        string="Jusqu'au"
    )

    next_invoice_date = fields.Date(
        string="Prochaine facture",
    )

    payment_term_id = fields.Many2one(
        'account.payment.term',
        string='Conditions de paiement'
    )

    start_date = fields.Date(
        string='Date début',
        default=fields.Date.today,
        required=True
    )

    expiration_date = fields.Date(
        string='Expiration'
    )

    delivery_date = fields.Date(
        string='Date de livraison'
    )



    activity_id = fields.Many2one(
        'amarna.activity',
        string='Activity'
    )

    plan_id = fields.Many2one(
        'amarna.subscription.plan',
        string='Subscription Plan'
    )

    remaining_sessions = fields.Integer(
        string='Remaining Sessions'
    )

    active = fields.Boolean(
        default=True
    )

    invoice_id = fields.Many2one(
        'account.move',
        string='Facture'
    )

    invoice_count = fields.Integer(
        string="Factures",
        compute="_compute_invoice_count"
    )

    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        store=True,
        readonly=True
    )

    recurring_amount = fields.Monetary(
        string="Récurrent",
        currency_field="currency_id",
        compute="_compute_recurring_amount",
        store=True,
    )

    # =====================================================
    # ETAT
    # =====================================================

    state = fields.Selection([
        ('draft', 'Devis'),
        ('sent', 'Envoyé'),
        ('sale', 'Commande client'),
        ('cancel', 'Annulé'),
    ], default='draft', tracking=True)

    # =====================================================
    # LIGNES
    # =====================================================

    line_ids = fields.One2many(
        'amarna.subscription.line',
        'subscription_id',
        string='Lignes'
    )

    # =====================================================
    # TOTAUX
    # =====================================================

    amount_total = fields.Monetary(
        string="Total",
        currency_field="currency_id",
        compute="_compute_amounts",
        store=True
    )


    amount_untaxed = fields.Float(
        string='Montant HT',
        compute='_compute_amounts',)

    amount_untaxed = fields.Monetary(
        string="Montant HT",
        currency_field="currency_id",
        compute="_compute_amounts",
        store=True
    )

    sale_person_id = fields.Many2one(
        'res.users',
        string='Vendeur',
        default=lambda self: self.env.user
    )

    client_reference = fields.Char(
        string='Référence client'
    )

    campaign = fields.Char(
        string='Campagne'
    )

    medium = fields.Char(
        string='Médium'
    )

    source = fields.Char(
        string='Source'
    )

    # =====================================================
    # NOTES
    # =====================================================

    note = fields.Text(
        string='Notes'
    )

    # =====================================================
    # COMPUTE
    # =====================================================

    @api.depends('line_ids.subtotal')
    def _compute_amounts(self):
        for rec in self:
            rec.amount_untaxed = sum(
                rec.line_ids.mapped('subtotal')
            )
            rec.amount_total = rec.amount_untaxed

    @api.depends('line_ids.price_subtotal')
    def _compute_recurring_amount(self):
        for rec in self:
            rec.recurring_amount = sum(rec.line_ids.mapped('price_subtotal'))

    @api.depends('order_date', 'recurring_plan_id')
    def _compute_expiration(self):
        for rec in self:
            rec.expiration_date = rec.next_invoice_date

    @api.onchange('order_date', 'recurring_plan_id')
    def _onchange_plan(self):
        for rec in self:
            if rec.order_date and rec.recurring_plan_id:
                rec.expiration_date = (
                        rec.order_date.date()
                        + timedelta(days=rec.recurring_plan_id.duration_days)
                )

                rec.next_invoice_date = rec.expiration_date


    @api.depends('line_ids.price_subtotal')
    def _compute_amounts(self):

        for rec in self:
            rec.amount_untaxed = sum(
                rec.line_ids.mapped('price_subtotal')
            )

            rec.amount_total = rec.amount_untaxed



    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = 1 if rec.invoice_id else 0

    @api.depends('state', 'payment_state')
    def _compute_subscription_status(self):
        for rec in self:

            if rec.state == 'draft':
                rec.subscription_status = 'draft'

            elif rec.state in ('sent', 'sale'):
                rec.subscription_status = 'running'

            elif rec.state == 'cancel':
                rec.subscription_status = 'cancel'

            else:
                rec.subscription_status = 'draft'

    # =====================================================
    # ONCHANGE
    # =====================================================

    @api.onchange('plan_id')
    def _onchange_plan_id(self):

        if self.plan_id:

            self.activity_id = self.plan_id.activity_id

            self.remaining_sessions = (
                self.plan_id.session_count
            )

            if self.start_date:

                self.expiration_date = (
                    self.start_date +
                    timedelta(days=self.plan_id.duration_days)
                )

    # =====================================================
    # ACTIONS
    # =====================================================

    def action_send(self):
        self.write({
            'state': 'sent'
        })

    def action_confirm(self):
        self.write({
            'state': 'sale'
        })

    def action_cancel(self):
        self.write({
            'state': 'cancel'
        })

    def action_draft(self):
        self.write({
            'state': 'draft'
        })

    # =====================================================
    # FACTURE
    # =====================================================


    invoice_state = fields.Selection(
        related="invoice_id.state",
        string="État facture",
        store=True,
        readonly=True,
    )

    payment_state = fields.Selection(
        related="invoice_id.payment_state",
        string="État paiement",
        store=True,
        readonly=True,
    )

    subscription_status = fields.Selection(
        [
            ('draft', 'Devis'),
            ('running', 'En cours'),
            ('paid', 'Payé'),
            ('closed', 'Clos'),
            ('cancel', 'Annulé'),
        ],
        string="Statut d'abonnement",
        compute="_compute_subscription_status",
        store=True,
        tracking=True,
    )


    def action_print_subscription(self):
        return True

    def action_preview_subscription(self):
        return True

    def action_discount(self):
        return True

    def action_create_invoice(self):

        self.ensure_one()

        invoice_lines = []

        for line in self.line_ids:

            invoice_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'quantity': line.product_uom_qty,
                'price_unit': line.price_unit,
                'name': line.name,
            }))

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_line_ids': invoice_lines,
        })

        self.invoice_id = invoice.id

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': invoice.id,
        }

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'amarna.subscription'
            ) or 'New'

        return super().create(vals)


    def action_view_invoice(self):
        self.ensure_one()

        if not self.invoice_id:
            return True

        return {
            'type': 'ir.actions.act_window',
            'name': 'Facture',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.invoice_id.id,
        }
