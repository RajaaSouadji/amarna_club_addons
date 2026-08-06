# -*- coding: utf-8 -*-
from odoo import fields, models


class AmarnaClubActivity(models.Model):
    _inherit = 'amarna.club.activity'

    subscription_activity_id = fields.Many2one(
        'amarna.club.activity',
        string='Activité abonnement',
        help='Lien optionnel vers l’activité correspondante du module abonnement.',
    )
