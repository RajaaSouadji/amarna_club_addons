# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models


class AmarnaClubAsset(models.Model):
    _inherit = 'amarna.club.asset'

    intervention_ids = fields.One2many(
        'amarna.club.intervention', 'asset_id', string='Interventions')
    open_intervention_count = fields.Integer(
        string='Interventions ouvertes', compute='_compute_open_intervention_count')

    @api.depends('intervention_ids.status')
    def _compute_open_intervention_count(self):
        counts = dict(self.env['amarna.club.intervention']._read_group(
            [('asset_id', 'in', self.ids), ('status', '!=', 'resolved')],
            ['asset_id'], ['__count']))
        for rec in self:
            rec.open_intervention_count = counts.get(rec, 0)

    def action_view_interventions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': 'Interventions',
            'res_model': 'amarna.club.intervention', 'view_mode': 'list,kanban,form',
            'domain': [('asset_id', '=', self.id)],
            'context': {'default_asset_id': self.id,
                        'default_mobile_asset_code': self.code,
                        'default_activity_id': self.activity_id.id},
        }

    @api.model
    def _cron_create_preventive_tickets(self):
        """Plan a preventive ticket ahead of each equipment's next maintenance."""
        Ticket = self.env['amarna.club.intervention']
        lead = self.env.company.amarna_preventive_lead_days
        horizon = fields.Datetime.now() + timedelta(days=lead)
        assets = self.search([
            ('maintenance_interval_days', '>', 0),
            ('next_maintenance', '!=', False),
            ('next_maintenance', '<=', horizon)])
        busy = Ticket.search([
            ('asset_id', 'in', assets.ids), ('type', '=', 'preventive'),
            ('status', '!=', 'resolved')]).asset_id
        created = Ticket
        for asset in assets - busy:
            created |= Ticket.create({
                'name': 'Entretien préventif : %s' % asset.name,
                'type': 'preventive', 'priority': 'medium',
                'asset_id': asset.id, 'mobile_asset_code': asset.code,
                'activity_id': asset.activity_id.id,
                'staff_id': asset.staff_id.id,
                'date_due': asset.next_maintenance,
            })
        return created
