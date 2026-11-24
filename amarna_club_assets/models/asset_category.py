# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AmarnaClubAssetCategory(models.Model):
    """Equipment category (as in Odoo Maintenance): carries the defaults an
    equipment inherits, such as the preventive maintenance interval."""
    _name = 'amarna.club.asset.category'
    _description = "Catégorie d'équipement"
    _order = 'name'

    name = fields.Char(string='Catégorie', required=True, translate=True)
    color = fields.Integer(string='Couleur')
    maintenance_interval_days = fields.Integer(
        string='Entretien préventif tous les (jours)',
        help="Intervalle repris par défaut par les équipements de cette "
             "catégorie. 0 = pas d'entretien préventif planifié.")
    staff_id = fields.Many2one(
        'amarna.club.staff', string='Technicien par défaut',
        help="Responsable proposé pour les équipements de cette catégorie.")
    note = fields.Text(string='Notes')
    asset_ids = fields.One2many('amarna.club.asset', 'category_id', string='Équipements')
    asset_count = fields.Integer(compute='_compute_asset_count')
    active = fields.Boolean(default=True)

    _name_uniq = models.Constraint('unique (name)', 'Cette catégorie existe déjà.')

    @api.depends('asset_ids')
    def _compute_asset_count(self):
        counts = dict(self.env['amarna.club.asset']._read_group(
            [('category_id', 'in', self.ids)], ['category_id'], ['__count']))
        for rec in self:
            rec.asset_count = counts.get(rec, 0)
