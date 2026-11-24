# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AmarnaClubActivity(models.Model):
    """Lifeguard supervision of the pool, on the activity card."""
    _inherit = 'amarna.club.activity'

    lifeguard_count = fields.Integer(
        string='Maîtres-nageurs affectés', compute='_compute_lifeguard_ratio')
    bathers_per_lifeguard = fields.Float(
        string='Baigneurs par maître-nageur', compute='_compute_lifeguard_ratio')
    lifeguard_ratio_ok = fields.Boolean(
        string='Surveillance suffisante', compute='_compute_lifeguard_ratio',
        help="Faux quand il y a des baigneurs et trop peu de maîtres-nageurs "
             "affectés, selon le ratio maximal défini dans les paramètres.")
    pool_auto_closed = fields.Boolean(
        string='Fermée automatiquement', readonly=True, copy=False,
        help="Fermée par un relevé d'eau non conforme : rouverte au prochain relevé conforme.")

    @api.depends('staff_ids.role', 'current_occupancy')
    def _compute_lifeguard_ratio(self):
        limit = self.env.company.amarna_pool_max_bathers_per_lifeguard
        for rec in self:
            guards = len(rec.staff_ids.filtered(lambda s: s.role == 'lifeguard'))
            rec.lifeguard_count = guards
            if guards:
                rec.bathers_per_lifeguard = rec.current_occupancy / guards
            else:
                rec.bathers_per_lifeguard = float(rec.current_occupancy)
            rec.lifeguard_ratio_ok = (
                not rec.current_occupancy
                or (guards > 0 and rec.bathers_per_lifeguard <= limit))
