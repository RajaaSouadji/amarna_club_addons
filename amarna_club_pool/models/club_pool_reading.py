# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AmarnaClubPoolReading(models.Model):
    _name = 'amarna.club.pool.reading'
    _description = "Relevé qualité de l'eau (piscine)"
    _order = 'reading_time desc'
    _rec_name = 'reading_time'

    reading_time = fields.Datetime(
        string='Date du relevé',
        default=fields.Datetime.now,
        required=True,
    )

    temperature = fields.Float(string='Température (°C)', group_operator='avg')

    chlorine = fields.Float(string='Chlore (mg/L)', group_operator='avg')

    ph = fields.Float(string='pH', group_operator='avg')

    turbidity = fields.Float(string='Turbidité (NTU)', group_operator='avg')

    author = fields.Char(
        string='Relevé par (mobile)',
        help="Nom de l'employé saisi dans l'application tablette.",
    )

    user_id = fields.Many2one(
        'res.users',
        string='Utilisateur',
        default=lambda self: self.env.user,
    )

    notes = fields.Text(string='Notes')

    # Rules come from the club settings (Configuration > Piscine); the app
    # receives the same values through amarna_app_config().
    temperature_ok = fields.Boolean(string='Température conforme', compute='_compute_conformity', store=True)
    chlorine_ok = fields.Boolean(string='Chlore conforme', compute='_compute_conformity', store=True)
    ph_ok = fields.Boolean(string='pH conforme', compute='_compute_conformity', store=True)
    turbidity_ok = fields.Boolean(string='Turbidité conforme', compute='_compute_conformity', store=True)

    issue_count = fields.Integer(
        string='Paramètres hors norme',
        compute='_compute_conformity',
        store=True,
    )

    conform = fields.Boolean(
        string='Conforme',
        compute='_compute_conformity',
        store=True,
    )

    score = fields.Float(
        string='Score global',
        group_operator='avg',
        compute='_compute_conformity',
        store=True,
    )

    @api.depends('temperature', 'chlorine', 'ph', 'turbidity')
    def _compute_conformity(self):
        company = self.env.company
        for rec in self:
            rec.temperature_ok = (company.amarna_pool_temp_min
                                  <= rec.temperature <= company.amarna_pool_temp_max)
            rec.chlorine_ok = (company.amarna_pool_chlorine_min
                               <= rec.chlorine <= company.amarna_pool_chlorine_max)
            rec.ph_ok = company.amarna_pool_ph_min <= rec.ph <= company.amarna_pool_ph_max
            rec.turbidity_ok = rec.turbidity <= company.amarna_pool_turbidity_max
            checks = [rec.temperature_ok, rec.chlorine_ok,
                      rec.ph_ok, rec.turbidity_ok]
            rec.issue_count = checks.count(False)
            rec.conform = rec.issue_count == 0
            score = 100.0
            if not rec.temperature_ok:
                score -= company.amarna_pool_weight_temperature
            if not rec.chlorine_ok:
                score -= company.amarna_pool_weight_chlorine
            if not rec.ph_ok:
                score -= company.amarna_pool_weight_ph
            if not rec.turbidity_ok:
                score -= company.amarna_pool_weight_turbidity
            rec.score = max(score, 0.0)
