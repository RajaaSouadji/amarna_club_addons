# -*- coding: utf-8 -*-
from odoo import fields, models


class AmarnaClubAssetService(models.Model):
    _inherit = 'amarna.club.asset.service'

    intervention_id = fields.Many2one(
        'amarna.club.intervention', string='Ticket', ondelete='set null', copy=False)
