from odoo import models, fields


class AmarnaSubscriptionType(models.Model):
    _name = 'amarna.subscription.type'
    _description = 'Subscription Type'
    _rec_name = 'name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)