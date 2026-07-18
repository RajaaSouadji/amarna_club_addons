# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AmarnaClubActivity(models.Model):
    _inherit = 'amarna.club.activity'

    subscription_activity_id = fields.Many2one(
        'amarna.activity',
        string='Activité Abonnement',
        help="Lien optionnel vers l'activité correspondante du module "
             "Abonnement (plans et souscriptions).",
    )

    subscription_plan_count = fields.Integer(
        compute='_compute_subscription_plan_count',
        string="Plans d'abonnement",
    )

    @api.depends('subscription_activity_id',
                 'subscription_activity_id.subscription_plan_ids')
    def _compute_subscription_plan_count(self):
        for rec in self:
            rec.subscription_plan_count = len(
                rec.subscription_activity_id.subscription_plan_ids
            ) if rec.subscription_activity_id else 0
