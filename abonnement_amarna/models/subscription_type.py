# -*- coding: utf-8 -*-
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError

UNIT_LABELS = {'day': 'Jour(s)', 'week': 'Semaine(s)', 'month': 'Mois', 'year': 'Année(s)'}


class AmarnaSubscriptionType(models.Model):
    """Durée d'une formule : 1 mois, 3 mois, 1 an, etc.

    Calendar arithmetic is used (a month is a month, not 30 days), so a
    subscription that starts on 15 January expires on 14 February.
    """
    _name = 'amarna.subscription.type'
    _description = 'Durée d’abonnement'
    _order = 'active desc, name'

    name = fields.Char(string='Nom', required=True)
    duration_value = fields.Integer(string='Durée', default=1, required=True)
    duration_unit = fields.Selection(
        list(UNIT_LABELS.items()), string='Unité', default='month', required=True)
    duration_summary = fields.Char(
        string='Résumé', compute='_compute_duration_summary')
    active = fields.Boolean(default=True)

    @api.depends('duration_value', 'duration_unit')
    def _compute_duration_summary(self):
        for record in self:
            record.duration_summary = '%s %s' % (
                record.duration_value, UNIT_LABELS.get(record.duration_unit, ''))

    @api.constrains('duration_value')
    def _check_duration_value(self):
        for record in self:
            if record.duration_value <= 0:
                raise ValidationError('La durée doit être supérieure à zéro.')

    def _end_date(self, start):
        """Last day of validity for a subscription starting on ``start``."""
        self.ensure_one()
        delta = {
            'day': relativedelta(days=self.duration_value),
            'week': relativedelta(weeks=self.duration_value),
            'month': relativedelta(months=self.duration_value),
            'year': relativedelta(years=self.duration_value),
        }[self.duration_unit]
        return start + delta - timedelta(days=1)
