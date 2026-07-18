from odoo import models, fields , api


class AmarnaRecurringPlanLine(models.Model):
    _name = 'amarna.recurring.plan.line'
    _description = 'Recurring Plan Line'

    plan_id = fields.Many2one(
        'amarna.recurring.plan',
        required=True,
        ondelete='cascade'
    )

    product_id = fields.Many2one(
        'product.product',
        string='Produit',
        required=True
    )

    price_unit = fields.Float(
        string="Prix unitaire"
    )

    validity_number = fields.Integer(
        string='Validité',
        default=1
    )

    validity_unit_id = fields.Many2one(
        'amarna.duration.unit',
        string='Unité'
    )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.price_unit = self.product_id.list_price