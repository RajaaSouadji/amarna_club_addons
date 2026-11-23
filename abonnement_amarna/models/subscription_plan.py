# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AmarnaSubscriptionPlan(models.Model):
    """Formule commerciale : une activité, une durée, un prix, un nombre de séances.

    ``session_count = 0`` means an unlimited formula (no session counter).
    """
    _name = 'amarna.subscription.plan'
    _inherit = ['mail.thread']
    _description = 'Formule d’abonnement'
    _order = 'activity_id, name'

    name = fields.Char(string='Formule', required=True, tracking=True)
    active = fields.Boolean(default=True)
    activity_id = fields.Many2one(
        'amarna.club.activity', string='Activité', required=True, tracking=True)
    subscription_type_id = fields.Many2one(
        'amarna.subscription.type', string='Durée', required=True, tracking=True)
    duration_summary = fields.Char(
        related='subscription_type_id.duration_summary', string='Durée affichée')
    list_price = fields.Float(
        string='Prix HT', required=True, default=0.0, tracking=True,
        help="Prix hors taxes facturé à chaque période de l'abonnement.")
    tax_ids = fields.Many2many(
        'account.tax', 'amarna_plan_tax_rel', 'plan_id', 'tax_id',
        string='Taxes (TVA)', domain="[('type_tax_use', 'in', ('sale', 'all'))]",
        default=lambda self: self.env.company.amarna_default_tax_id.ids,
        help="TVA appliquée à chaque période facturée de cette formule.")
    session_count = fields.Integer(
        string='Séances incluses', default=0, required=True, tracking=True,
        help="Nombre de passages inclus. 0 = formule illimitée.")
    product_id = fields.Many2one(
        'product.product', string='Produit de facturation',
        help="Laisser vide : un produit de service est créé automatiquement.")
    description = fields.Html(string='Description')
    subscription_count = fields.Integer(compute='_compute_subscription_count')

    _session_count_positive = models.Constraint(
        'CHECK(session_count >= 0)',
        'Le nombre de séances ne peut pas être négatif.')
    _list_price_positive = models.Constraint(
        'CHECK(list_price >= 0)',
        'Le prix ne peut pas être négatif.')

    @api.constrains('list_price')
    def _check_list_price(self):
        for plan in self:
            if plan.list_price < 0:
                raise ValidationError('Le prix de la formule ne peut pas être négatif.')

    def _compute_subscription_count(self):
        counts = self.env['amarna.subscription']._read_group(
            [('plan_id', 'in', self.ids)], ['plan_id'], ['__count'])
        mapped = {plan.id: count for plan, count in counts}
        for plan in self:
            plan.subscription_count = mapped.get(plan.id, 0)

    def _get_billing_product(self):
        self.ensure_one()
        if self.product_id:
            return self.product_id
        return self.env['product.product']._amarna_service(
            'AMARNA-PLAN-%s' % self.id, 'Abonnement – %s' % self.name)

    def _billing_line_vals(self):
        """Values of the subscription line created from this plan."""
        self.ensure_one()
        product = self._get_billing_product()
        return {
            'product_id': product.id,
            'name': self.name,
            'product_uom_qty': 1.0,
            'price_unit': self.list_price,
            'tax_ids': [(6, 0, self.tax_ids.ids)],
        }

    def action_view_subscriptions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Abonnements',
            'res_model': 'amarna.subscription',
            'view_mode': 'tree,form',
            'domain': [('plan_id', '=', self.id)],
            'context': {'default_plan_id': self.id},
        }
