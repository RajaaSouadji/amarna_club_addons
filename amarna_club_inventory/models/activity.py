# -*- coding: utf-8 -*-
from odoo import fields, models


class AmarnaClubActivity(models.Model):
    _inherit = 'amarna.club.activity'

    low_stock_count = fields.Integer(
        string='Consommables en stock bas', compute='_compute_low_stock_count')

    def _compute_low_stock_count(self):
        items = dict(self.env['amarna.club.inventory.item']._read_group(
            [('activity_id', 'in', self.ids), ('is_low', '=', True)],
            ['activity_id'], ['__count']))
        for rec in self:
            rec.low_stock_count = items.get(rec, 0)
