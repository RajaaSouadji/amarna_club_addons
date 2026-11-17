# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    amarna_default_tax_id = fields.Many2one(
        related='company_id.amarna_default_tax_id', readonly=False,
        domain="[('type_tax_use', 'in', ('sale', 'all'))]")
    amarna_opening_hour = fields.Float(related='company_id.amarna_opening_hour', readonly=False)
    amarna_closing_hour = fields.Float(related='company_id.amarna_closing_hour', readonly=False)
    amarna_default_start_hour = fields.Float(related='company_id.amarna_default_start_hour', readonly=False)
    amarna_default_end_hour = fields.Float(related='company_id.amarna_default_end_hour', readonly=False)
    amarna_expiry_warning_days = fields.Integer(related='company_id.amarna_expiry_warning_days', readonly=False)
    amarna_ticket_due_days = fields.Integer(related='company_id.amarna_ticket_due_days', readonly=False)
    amarna_booking_horizon_days = fields.Integer(related='company_id.amarna_booking_horizon_days', readonly=False)
    amarna_default_people_count = fields.Integer(related='company_id.amarna_default_people_count', readonly=False)
    amarna_report_period_days = fields.Char(related='company_id.amarna_report_period_days', readonly=False)
    amarna_report_default_days = fields.Integer(related='company_id.amarna_report_default_days', readonly=False)
    amarna_support_phone = fields.Char(related='company_id.amarna_support_phone', readonly=False)
    amarna_support_email = fields.Char(related='company_id.amarna_support_email', readonly=False)
    amarna_support_hours = fields.Char(related='company_id.amarna_support_hours', readonly=False)
