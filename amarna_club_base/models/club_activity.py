# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AmarnaClubActivity(models.Model):
    _name = 'amarna.club.activity'
    _description = 'Activité du club'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    icon_key = fields.Char(string='Icône mobile')
    mobile_status = fields.Selection([
        ('open', 'Ouvert'),
        ('closed', 'Fermé'),
        ('warning', 'Attention'),
        ('maintenance', 'En maintenance'),
    ], string='Statut opérationnel', default='open')
    closure_start = fields.Datetime(string='Fermeture du')
    closure_end = fields.Datetime(string='Fermeture au')
    current_occupancy = fields.Integer(string='Occupation actuelle')
    max_capacity = fields.Integer(string='Capacité maximale')
    assigned_staff = fields.Char(string='Personnel en service')
    occupancy_pct = fields.Float(
        string="Taux d'occupation (%)",
        compute='_compute_occupancy_pct',
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Couleur')

    _sql_constraints = [
        ('code_uniq', 'unique(code)', "Le code d'activité doit être unique."),
    ]

    @api.constrains('closure_start', 'closure_end')
    def _check_closure_period(self):
        for activity in self:
            if activity.closure_start and activity.closure_end and activity.closure_end <= activity.closure_start:
                raise ValidationError(
                    'La fin de fermeture doit être postérieure au début de fermeture.'
                )

    @api.depends('current_occupancy', 'max_capacity')
    def _compute_occupancy_pct(self):
        for rec in self:
            rec.occupancy_pct = (
                rec.current_occupancy * 100.0 / rec.max_capacity
                if rec.max_capacity else 0.0
            )

    @api.model
    def _find_by_mobile_code(self, code):
        if not code:
            return self.browse()
        return self.search(
            ['|', ('code', '=ilike', code), ('name', '=ilike', code)],
            limit=1,
        )
