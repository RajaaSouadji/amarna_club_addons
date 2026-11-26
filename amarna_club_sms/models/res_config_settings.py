# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    amarna_sms_expiry_enabled = fields.Boolean(related='company_id.amarna_sms_expiry_enabled', readonly=False)
    amarna_sms_expiry_days = fields.Integer(related='company_id.amarna_sms_expiry_days', readonly=False)
    amarna_sms_expiry_body = fields.Text(related='company_id.amarna_sms_expiry_body', readonly=False)
