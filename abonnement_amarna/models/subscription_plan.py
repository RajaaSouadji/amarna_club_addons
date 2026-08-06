from odoo import api, fields, models


class AmarnaSubscriptionPlan(models.Model):
    _name = "amarna.subscription.plan"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Subscription Plan"
    _order = "name"

    # ==========================================================
    # GENERAL
    # ==========================================================

    name = fields.Char(
        string="Plan",
        required=True,
        tracking=True,
    )

    active = fields.Boolean(
        default=True,
        tracking=True,
    )

    activity_id = fields.Many2one(
        "amarna.club.activity",
        string="Activité concernée",
        required=True,
        tracking=True,
    )

    subscription_type_id = fields.Many2one(
        "amarna.subscription.type",
        string="Type abonnement",
        required=True,
    )

    product_id = fields.Many2one(
        "product.product",
        string="Produit de facturation",
        required=False,
        tracking=True,
    )

    # ==========================================================
    # PRODUCT INFORMATION
    # ==========================================================

    image_1920 = fields.Image(
        related="product_id.image_1920",
        readonly=True,
    )

    list_price = fields.Float(
        string="Prix du plan",
        help="Prix appliqué à chaque abonnement utilisant ce plan. "
             "Il est indépendant du prix de vente du produit.",
        tracking=True,
    )

    currency_id = fields.Many2one(
        related="product_id.currency_id",
        readonly=True,
        store=True,

    )

    # ==========================================================
    # SUBSCRIPTION
    # ==========================================================

    session_count = fields.Integer(
        string="Séances incluses",
        default=0,
        required=True,
    )

    duration_days = fields.Integer(
        related='subscription_type_id.duration_days',
        string='Durée (jours)',
        readonly=True,
        store=True,
    )

    product_template_id = fields.Many2one(
        related="product_id.product_tmpl_id",
        readonly=True,
    )

    # ==========================================================
    # DESCRIPTION
    # ==========================================================

    description = fields.Html(
        string="Description"
    )

    note = fields.Html(
        string="Internal Notes"
    )
    # ==========================================================
    # SMART BUTTONS
    # ==========================================================

    subscription_count = fields.Integer(
        compute="_compute_subscription_count"
    )

    @api.depends()
    def _compute_subscription_count(self):
        for plan in self:
            plan.subscription_count = self.env[
                "amarna.subscription"
            ].search_count([
                ("plan_id", "=", plan.id)
            ])

    def action_view_product(self):
        self.ensure_one()
        if not self.product_id:
            return True

        return {
            "type": "ir.actions.act_window",
            "name": "Product",
            "res_model": "product.product",
            "res_id": self.product_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_subscriptions(self):
        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "name": "Subscriptions",
            "res_model": "amarna.subscription",
            "view_mode": "tree,form",
            "domain": [("plan_id", "=", self.id)],
            "context": {
                "default_plan_id": self.id,
            },
            "target": "current",
        }




