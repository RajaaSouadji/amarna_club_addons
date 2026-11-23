# -*- coding: utf-8 -*-
from odoo import fields, models


class AmarnaClubActivity(models.Model):
    _inherit = 'amarna.club.activity'

    open_ticket_count = fields.Integer(
        string='Interventions ouvertes', compute='_compute_open_ticket_count')

    def _compute_open_ticket_count(self):
        tickets = dict(self.env['amarna.club.intervention']._read_group(
            [('activity_id', 'in', self.ids), ('status', '!=', 'resolved')],
            ['activity_id'], ['__count']))
        for rec in self:
            rec.open_ticket_count = tickets.get(rec, 0)
