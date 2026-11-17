# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    amarna_horse_fatigue_alert = fields.Float(related='company_id.amarna_horse_fatigue_alert', readonly=False)
    amarna_horse_fatigue_rested = fields.Float(related='company_id.amarna_horse_fatigue_rested', readonly=False)
    amarna_farrier_interval_days = fields.Integer(related='company_id.amarna_farrier_interval_days', readonly=False)
    amarna_deworming_interval_days = fields.Integer(related='company_id.amarna_deworming_interval_days', readonly=False)
