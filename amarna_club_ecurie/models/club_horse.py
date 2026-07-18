# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models


class AmarnaClubHorse(models.Model):
    _name = 'amarna.club.horse'
    _description = 'Cheval du club'
    _order = 'box_number, name'

    name = fields.Char(required=True)

    code = fields.Char(
        string='Code mobile',
        index=True,
        copy=False,
        help="Identifiant du cheval dans l'application tablette (ex: h1).",
    )

    breed = fields.Char(string='Race')

    age = fields.Integer(string='Âge')

    box_number = fields.Char(string='Box')

    # Selection keys match the app's HorseStatus enum names.
    status = fields.Selection(
        [
            ('available', 'Disponible'),
            ('resting', 'Au repos'),
            ('injured', 'Blessé'),
        ],
        default='available',
        string='Statut',
    )

    fatigue = fields.Float(
        string='Fatigue (0-1)',
        help='Niveau de fatigue entre 0.0 (reposé) et 1.0 (épuisé), '
             "tel qu'affiché par la jauge de l'application.",
    )

    fatigue_pct = fields.Float(
        string='Fatigue (%)',
        compute='_compute_fatigue_pct',
    )

    diet = fields.Char(string='Alimentation')

    vet_note = fields.Text(string='Note vétérinaire')

    next_vet_visit = fields.Datetime(string='Prochaine visite vétérinaire')

    last_farrier = fields.Date(string='Dernier maréchal-ferrant')

    last_vaccine = fields.Date(string='Dernier vaccin')

    last_deworming = fields.Date(string='Dernier vermifuge')

    farrier_due = fields.Boolean(
        string='Ferrage à prévoir',
        compute='_compute_care_due',
        search='_search_farrier_due',
        help='Ferrage recommandé toutes les ~6 semaines (42 jours).',
    )

    deworming_due = fields.Boolean(
        string='Vermifuge à prévoir',
        compute='_compute_care_due',
        search='_search_deworming_due',
        help='Vermifuge recommandé tous les ~3 mois (90 jours).',
    )

    active = fields.Boolean(default=True)

    @api.depends('fatigue')
    def _compute_fatigue_pct(self):
        for rec in self:
            rec.fatigue_pct = rec.fatigue * 100.0

    def _search_care_due(self, field_name, days, operator, value):
        cutoff = fields.Date.context_today(self) - timedelta(days=days)
        want_due = bool(value) == (operator == '=')
        if want_due:
            return [(field_name, '!=', False), (field_name, '<', cutoff)]
        return ['|', (field_name, '=', False), (field_name, '>=', cutoff)]

    def _search_farrier_due(self, operator, value):
        return self._search_care_due('last_farrier', 42, operator, value)

    def _search_deworming_due(self, operator, value):
        return self._search_care_due('last_deworming', 90, operator, value)

    @api.depends('last_farrier', 'last_deworming')
    def _compute_care_due(self):
        # Same thresholds as the app (horses_provider.dart).
        today = fields.Date.context_today(self)
        for rec in self:
            rec.farrier_due = bool(
                rec.last_farrier
                and today - rec.last_farrier > timedelta(days=42)
            )
            rec.deworming_due = bool(
                rec.last_deworming
                and today - rec.last_deworming > timedelta(days=90)
            )
