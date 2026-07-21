# -*- coding: utf-8 -*-
from odoo import fields, models


class AmarnaSubscriptionHistory(models.Model):
    _name = 'amarna.subscription.history'
    _description = 'Historique des abonnements'
    _order = 'start_date desc, id desc'

    subscription_id = fields.Many2one('amarna.subscription', required=True, ondelete='cascade')
    partner_id = fields.Many2one(related='subscription_id.partner_id', store=True, readonly=True)
    plan_id = fields.Many2one('amarna.subscription.plan', string='Plan', required=True)
    start_date = fields.Date(required=True)
    expiration_date = fields.Date(required=True)
    amount = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one(related='subscription_id.currency_id', readonly=True)
    reason = fields.Selection([
        ('initial', 'Création'), ('renewal', 'Renouvellement'), ('change', 'Changement de plan'),
    ], default='initial', required=True)
    note = fields.Text()
