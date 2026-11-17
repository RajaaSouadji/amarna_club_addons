# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    amarna_weapon_cleaning_days = fields.Integer(
        related='company_id.amarna_weapon_cleaning_days', readonly=False)
