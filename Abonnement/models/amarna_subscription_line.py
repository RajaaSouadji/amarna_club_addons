from odoo import api, fields, models


class AmarnaSubscriptionLine(models.Model):
    _name = "amarna.subscription.line"
    _description = "Subscription Line"
    _order = "sequence,id"

    sequence = fields.Integer(
        default=10
    )

    display_type = fields.Selection([
        ('line_section', 'Section'),
        ('line_note', 'Note')
    ])

    subscription_id = fields.Many2one(
        'amarna.subscription',
        string="Subscription",
        required=True,
        ondelete="cascade"
    )

    company_id = fields.Many2one(
        related="subscription_id.company_id",
        store=True,
        readonly=True
    )

    currency_id = fields.Many2one(
        related="subscription_id.currency_id",
        store=True,
        readonly=True
    )

    product_id = fields.Many2one(
        'product.product',
        string='Produit',
        required=True
    )

    quantity = fields.Float(
        string='Quantité',
        default=1.0
    )

    price_unit = fields.Float(
        string='Prix unitaire'
    )

    subtotal = fields.Float(
        string='Montant',
        compute='_compute_subtotal',
        store=True
    )

    discount = fields.Float(
        string='Remise (%)',
        default=0.0
    )

    @api.depends('quantity', 'price_unit', 'discount')
    def _compute_subtotal(self):
        for rec in self:
            amount = rec.quantity * rec.price_unit

            rec.subtotal = amount - (
                    amount * rec.discount / 100.0
            )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.price_unit = self.product_id.list_price

    name = fields.Text(
        string="Description"
    )

    product_uom_qty = fields.Float(
        string="Quantité",
        default=1.0
    )

    product_uom_id = fields.Many2one(
        'uom.uom',
        string="Unité"
    )

    price_unit = fields.Float(
        string="Prix unitaire"
    )

    tax_ids = fields.Many2many(
        'account.tax',
        string="Taxes"
    )

    discount = fields.Float(
        string="Rem.%",
        default=0.0
    )

    price_subtotal = fields.Monetary(
        string="Montant",
        currency_field="currency_id",
        compute="_compute_amount",
        store=True
    )

    @api.depends(
        'product_uom_qty',
        'price_unit',
        'discount'
    )
    def _compute_amount(self):

        for line in self:

            subtotal = (
                line.product_uom_qty *
                line.price_unit
            )

            subtotal -= subtotal * (
                line.discount / 100
            )

            line.price_subtotal = subtotal

    @api.onchange("product_id")
    def _onchange_product(self):

        if self.product_id:

            self.name = self.product_id.display_name

            self.price_unit = self.product_id.lst_price

            self.product_uom_id = self.product_id.uom_id

            self.tax_ids = self.product_id.taxes_id
