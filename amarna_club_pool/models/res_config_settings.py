# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    amarna_pool_temp_min = fields.Float(related='company_id.amarna_pool_temp_min', readonly=False)
    amarna_pool_temp_max = fields.Float(related='company_id.amarna_pool_temp_max', readonly=False)
    amarna_pool_chlorine_min = fields.Float(related='company_id.amarna_pool_chlorine_min', readonly=False)
    amarna_pool_chlorine_max = fields.Float(related='company_id.amarna_pool_chlorine_max', readonly=False)
    amarna_pool_ph_min = fields.Float(related='company_id.amarna_pool_ph_min', readonly=False)
    amarna_pool_ph_max = fields.Float(related='company_id.amarna_pool_ph_max', readonly=False)
    amarna_pool_turbidity_max = fields.Float(related='company_id.amarna_pool_turbidity_max', readonly=False)
    amarna_pool_weight_temperature = fields.Integer(related='company_id.amarna_pool_weight_temperature', readonly=False)
    amarna_pool_weight_chlorine = fields.Integer(related='company_id.amarna_pool_weight_chlorine', readonly=False)
    amarna_pool_weight_ph = fields.Integer(related='company_id.amarna_pool_weight_ph', readonly=False)
    amarna_pool_weight_turbidity = fields.Integer(related='company_id.amarna_pool_weight_turbidity', readonly=False)
    amarna_pool_max_bathers_per_lifeguard = fields.Integer(
        related='company_id.amarna_pool_max_bathers_per_lifeguard', readonly=False)
    amarna_pool_auto_close = fields.Boolean(related='company_id.amarna_pool_auto_close', readonly=False)
