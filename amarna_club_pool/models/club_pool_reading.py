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

    temperature = fields.Float(string='Température (°C)')

    chlorine = fields.Float(string='Chlore (mg/L)')

    ph = fields.Float(string='pH')

    turbidity = fields.Float(string='Turbidité (NTU)')

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

    # Conformity rules identical to the app (pool_gauges_screen.dart):
    # temperature 26-30 °C, chlorine 1.0-3.0 mg/L, pH 7.2-7.6,
    # turbidity <= 1.0 NTU. Score weights: 20/30/30/20.
    temperature_ok = fields.Boolean(compute='_compute_conformity', store=True)
    chlorine_ok = fields.Boolean(compute='_compute_conformity', store=True)
    ph_ok = fields.Boolean(compute='_compute_conformity', store=True)
    turbidity_ok = fields.Boolean(compute='_compute_conformity', store=True)

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
        compute='_compute_conformity',
        store=True,
    )

    @api.depends('temperature', 'chlorine', 'ph', 'turbidity')
    def _compute_conformity(self):
        for rec in self:
            rec.temperature_ok = 26.0 <= rec.temperature <= 30.0
            rec.chlorine_ok = 1.0 <= rec.chlorine <= 3.0
            rec.ph_ok = 7.2 <= rec.ph <= 7.6
            rec.turbidity_ok = rec.turbidity <= 1.0
            checks = [rec.temperature_ok, rec.chlorine_ok,
                      rec.ph_ok, rec.turbidity_ok]
            rec.issue_count = checks.count(False)
            rec.conform = rec.issue_count == 0
            score = 100.0
            if not rec.temperature_ok:
                score -= 20
            if not rec.chlorine_ok:
                score -= 30
            if not rec.ph_ok:
                score -= 30
            if not rec.turbidity_ok:
                score -= 20
            rec.score = max(score, 0.0)
