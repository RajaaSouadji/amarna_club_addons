# -*- coding: utf-8 -*-
"""Facturation partagée par les abonnements et les réservations.

Principe : la comptabilité Odoo (``account.move`` / ``account.payment``) est
la seule source de vérité pour les montants dus et payés. Les modèles métier
ne stockent aucun paiement : ils déduisent leur état de facturation de leurs
factures, et l'accès RFID en découle.

Un modèle qui utilise ce mixin doit fournir :
  * ``amount_total``        : montant TTC attendu (champ calculé à côté) ;
  * ``billing_period_start``: date de début de la période facturée ;
  * ``invoice_ids``         : One2many vers ``account.move`` via le champ
                              ``_billing_link_field`` ;
  * ``_billing_lines_vals()``: lignes de facture (HT), sans écriture en base ;
  * ``_sync_rfid_access()`` : recalcul des autorisations d'accès RFID.
"""
from odoo import api, fields, models
from odoo.exceptions import UserError

BILLING_STATE_SELECTION = [
    ('free', 'Gratuit'),
    ('to_invoice', 'À facturer'),
    ('unpaid', 'Facturé, non payé'),
    ('partial', 'Partiellement payé'),
    ('paid', 'Payé'),
]

EPSILON = 0.01


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _amarna_service(self, code, name):
        """Produit de service dédié à la facturation, retrouvé par son code."""
        product = self.with_context(active_test=False).search(
            [('default_code', '=', code)], limit=1)
        if product:
            return product
        return self.create({
            'name': name,
            'default_code': code,
            'type': 'service',
            'sale_ok': True,
            'purchase_ok': False,
        })


class AmarnaBillingMixin(models.AbstractModel):
    _name = 'amarna.billing.mixin'
    _description = 'Facturation partagée (abonnements et réservations)'

    # Each concrete model sets this to the account.move Many2one that links
    # an invoice back to it (e.g. "amarna_subscription_id").
    _billing_link_field = None

    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', readonly=True)
    payment_required = fields.Boolean(
        string='Paiement requis pour l’accès', default=True)

    amount_invoiced = fields.Monetary(
        string='Facturé (TTC)', currency_field='currency_id',
        compute='_compute_billing', store=True)
    amount_paid = fields.Monetary(
        string='Encaissé', currency_field='currency_id',
        compute='_compute_billing', store=True)
    amount_due = fields.Monetary(
        string='Reste à payer', currency_field='currency_id',
        compute='_compute_billing', store=True)
    billing_state = fields.Selection(
        BILLING_STATE_SELECTION, string='Facturation',
        compute='_compute_billing', store=True)
    payment_valid = fields.Boolean(
        string='Paiement à jour', compute='_compute_billing', store=True,
        help="Vrai lorsque la période en cours est gratuite ou entièrement "
             "payée. Conditionne l'accès RFID et les check-ins.")

    # ------------------------------------------------------------ Compute

    @api.depends(
        'amount_total', 'payment_required', 'billing_period_start',
        'invoice_ids.state', 'invoice_ids.move_type',
        'invoice_ids.amount_total', 'invoice_ids.amount_residual',
        'invoice_ids.amarna_period_start',
    )
    def _compute_billing(self):
        for rec in self:
            posted = rec._billing_current_invoices().filtered(
                lambda m: m.state == 'posted' and m.move_type == 'out_invoice')
            invoiced = sum(posted.mapped('amount_total'))
            paid = sum(m.amount_total - m.amount_residual for m in posted)
            due = invoiced - paid

            rec.amount_invoiced = invoiced
            rec.amount_paid = paid
            rec.amount_due = due
            if rec.amount_total <= EPSILON:
                state = 'free'
            elif not posted:
                state = 'to_invoice'
            elif due <= EPSILON:
                state = 'paid'
            elif paid > EPSILON:
                state = 'partial'
            else:
                state = 'unpaid'
            rec.billing_state = state
            rec.payment_valid = (not rec.payment_required) or state in ('free', 'paid')

    def _billing_current_invoices(self):
        """Invoices issued for the period being billed (not older periods)."""
        self.ensure_one()
        return self.invoice_ids.filtered(
            lambda m: m.amarna_period_start == self.billing_period_start)

    # ------------------------------------------------------------ Amounts

    def _billing_lines_vals(self):
        """Invoice lines as dicts: product, name, quantity, price_unit (HT),
        discount (%), tax_ids (recordset). Must not write to the database."""
        raise NotImplementedError

    def _billing_amounts(self):
        """(untaxed, total incl. tax) for one record, from its billing lines."""
        self.ensure_one()
        untaxed = total = 0.0
        for line in self._billing_lines_vals():
            price = line['price_unit'] * (1 - line.get('discount', 0.0) / 100.0)
            res = line['tax_ids'].compute_all(
                price, currency=self.currency_id,
                quantity=line.get('quantity', 1.0), partner=self.partner_id)
            untaxed += res['total_excluded']
            total += res['total_included']
        return untaxed, total

    # ----------------------------------------------------------- Invoices

    def _billing_invoice_vals(self):
        self.ensure_one()
        lines = []
        for line in self._billing_lines_vals():
            lines.append((0, 0, {
                'product_id': line['product'].id,
                'name': line['name'],
                'quantity': line.get('quantity', 1.0),
                'price_unit': line['price_unit'],
                'discount': line.get('discount', 0.0),
                'tax_ids': [(6, 0, line['tax_ids'].ids)],
            }))
        return {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id,
            'invoice_date': fields.Date.context_today(self),
            'invoice_origin': self.name,
            'amarna_period_start': self.billing_period_start,
            self._billing_link_field: self.id,
            'invoice_line_ids': lines,
        }

    def _billing_ensure_partner(self):
        """Invoices need a customer. Models may create one on the fly."""
        if not self.partner_id:
            raise UserError("Renseignez le membre avant de facturer.")

    def action_create_invoice(self):
        """Create and post the invoice for the current period."""
        moves = self.env['account.move']
        for rec in self:
            rec._billing_ensure_partner()
            if rec.billing_state == 'free':
                raise UserError("Ce montant est nul : aucune facture à émettre.")
            if rec.billing_state in ('unpaid', 'partial'):
                raise UserError(
                    "Une facture de cette période est déjà émise et reste à payer.")
            if rec.billing_state == 'paid':
                raise UserError("Cette période est déjà entièrement payée.")
            move = self.env['account.move'].create(rec._billing_invoice_vals())
            move.action_post()
            moves |= move
        if len(moves) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Facture',
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': moves.id,
            }
        return True

    def action_collect(self):
        """The desk button: invoice the period if that is not done yet, then open the
        payment window. Cash, cheque or card is the journal chosen in that window."""
        self.ensure_one()
        if self.billing_state == 'to_invoice':
            self.action_create_invoice()
        return self.action_register_payment()

    def action_register_payment(self):
        """Open the standard Odoo payment wizard on the open invoices."""
        self.ensure_one()
        open_invoices = self.invoice_ids.filtered(
            lambda m: m.state == 'posted' and m.move_type == 'out_invoice'
            and m.amount_residual > EPSILON)
        if not open_invoices:
            raise UserError("Aucune facture en attente de paiement.")
        return {
            'type': 'ir.actions.act_window',
            'name': 'Encaisser',
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': 'account.move',
                'active_ids': open_invoices.ids,
            },
        }

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Factures',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [(self._billing_link_field, '=', self.id)],
            'context': {'default_move_type': 'out_invoice'},
        }
