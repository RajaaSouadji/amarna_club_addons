from odoo import api, fields, models


class AmarnaActivity(models.Model):
    _name = "amarna.activity"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Activity"

    name = fields.Char(required=True, tracking=True)

    code = fields.Char(tracking=True)

    description = fields.Html()

    active = fields.Boolean(default=True)

    subscription_plan_ids = fields.One2many(
        "amarna.subscription.plan",
        "activity_id",
        string="Plans"
    )

    subscription_plan_count = fields.Integer(
        compute="_compute_subscription_plan_count"
    )

    image_1920 = fields.Image("Image", max_width=1920, max_height=1920)

    color = fields.Integer(
        string="Couleur"
    )

    sequence = fields.Integer(
        default=10
    )

    note = fields.Html(
        string="Notes internes"
    )

    @api.depends("subscription_plan_ids")
    def _compute_subscription_plan_count(self):
        for rec in self:
            rec.subscription_plan_count = len(rec.subscription_plan_ids)

    def action_view_subscription_plans(self):
        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "name": "Plans",
            "res_model": "amarna.subscription.plan",
            "view_mode": "tree,form",
            "domain": [("activity_id", "=", self.id)],
            "context": {
                "default_activity_id": self.id,
            },
        }