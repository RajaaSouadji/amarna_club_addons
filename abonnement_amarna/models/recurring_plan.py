from odoo import models, fields, api


class AmarnaRecurringPlan(models.Model):
    _name = 'amarna.recurring.plan'
    _description = 'Recurring Plan'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # =====================================================
    # MAIN INFO
    # =====================================================

    name = fields.Char(
        string='Name',
        required=True
    )

    duration_days = fields.Integer(
        string="Nombre de jours",
        required=True,
    )

    auto_close_limit = fields.Integer(
        string='Automatic Closing',
        default=15
    )

    active = fields.Boolean(
        default=True
    )



    # =====================================================
    # PRICING LINES
    # =====================================================

    recurring_line_ids = fields.One2many(
        'amarna.recurring.plan.line',
        'plan_id',
        string='Pricing'
    )

    # =====================================================
    # SMART BUTTONS
    # =====================================================

    subscription_count = fields.Integer(
        string='Subscriptions',
        compute='_compute_counts'
    )

    line_count = fields.Integer(
        string='Subscription Articles',
        compute='_compute_counts'
    )

    # =====================================================
    # COMPUTE
    # =====================================================

    @api.depends('recurring_line_ids')
    def _compute_counts(self):
        for rec in self:
            rec.line_count = len(rec.recurring_line_ids)
            subscription_obj = self.env['amarna.subscription']
            rec.subscription_count = subscription_obj.search_count([
                ('recurring_plan_id', '=', rec.id)
            ])

    # =====================================================
    # SMART BUTTON ACTIONS
    # =====================================================






    def action_view_subscriptions(self):
        self.ensure_one()

        return {
            'name': 'Subscriptions',
            'type': 'ir.actions.act_window',
            'res_model': 'amarna.subscription',
            'view_mode': 'tree,form',
            'domain': [('recurring_plan_id', '=', self.id)],
            'context': {
                'default_recurring_plan_id': self.id,
            }
        }

    def action_view_lines(self):
        self.ensure_one()

        return {
            'name': 'Pricing',
            'type': 'ir.actions.act_window',
            'res_model': 'amarna.recurring.plan.line',
            'view_mode': 'tree,form',
            'domain': [('plan_id', '=', self.id)],
            'context': {
                'default_plan_id': self.id,
            }
        }