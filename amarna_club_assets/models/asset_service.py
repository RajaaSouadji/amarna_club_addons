# -*- coding: utf-8 -*-

from odoo import api, fields, models

SERVICE_TYPES = [
    ('preventive', 'Entretien préventif'),
    ('repair', 'Réparation'),
    ('inspection', 'Contrôle / inspection'),
    ('cleaning', 'Nettoyage'),
    ('calibration', 'Étalonnage'),
]


class AmarnaClubAssetService(models.Model):
    """Maintenance journal of an equipment (as the service log of Odoo Fleet)."""
    _name = 'amarna.club.asset.service'
    _description = "Journal d'entretien"
    _order = 'date desc, id desc'

    asset_id = fields.Many2one(
        'amarna.club.asset', string='Équipement', required=True,
        ondelete='cascade', index=True)
    activity_id = fields.Many2one(related='asset_id.activity_id', store=True)
    service_type = fields.Selection(
        SERVICE_TYPES, string="Type d'intervention", required=True, default='preventive')
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    description = fields.Char(string='Description')
    staff_id = fields.Many2one('amarna.club.staff', string='Réalisé par')
    supplier_id = fields.Many2one('res.partner', string='Prestataire')
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)
    cost = fields.Monetary(string='Coût', currency_field='currency_id')
    notes = fields.Text(string='Notes')

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.mapped('asset_id')._refresh_maintenance_dates()
        return records

    def write(self, vals):
        assets = self.mapped('asset_id')
        result = super().write(vals)
        (assets | self.mapped('asset_id'))._refresh_maintenance_dates()
        return result

    def unlink(self):
        assets = self.mapped('asset_id')
        result = super().unlink()
        assets._refresh_maintenance_dates()
        return result

    @api.depends('asset_id', 'date', 'description')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s – %s' % (
                rec.asset_id.name or 'Entretien', rec.description or rec.date or '')
