from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AmarnaSubscriptionType(models.Model):
    _name = 'amarna.subscription.type'
    _description = 'Subscription Type'
    _rec_name = 'name'
    _order = 'active desc, name'

    name = fields.Char(string='Nom du type', required=True)
    duration_value = fields.Integer(string='Durée', default=1, required=True)
    duration_unit = fields.Selection([
        ('day', 'Jour(s)'),
        ('week', 'Semaine(s)'),
        ('month', 'Mois'),
        ('year', 'Année(s)'),
    ], string='Unité', default='month', required=True)
    duration_days = fields.Integer(
        string='Durée calculée (jours)', compute='_compute_duration_days',
        store=True, compute_sudo=True,
    )
    duration_summary = fields.Char(
        string='Résumé', compute='_compute_duration_summary',
        store=True, compute_sudo=True,
    )
    active = fields.Boolean(string='Actif', default=True)

    @api.depends('duration_value', 'duration_unit')
    def _compute_duration_days(self):
        factors = {'day': 1, 'week': 7, 'month': 30, 'year': 365}
        for record in self:
            record.duration_days = record.duration_value * factors.get(record.duration_unit, 30)

    @api.depends('duration_value', 'duration_unit', 'duration_days')
    def _compute_duration_summary(self):
        labels = dict(self._fields['duration_unit'].selection)
        for record in self:
            record.duration_summary = '%s %s = %s jours' % (
                record.duration_value,
                labels.get(record.duration_unit, ''),
                record.duration_days,
            )

    @api.constrains('duration_value')
    def _check_duration_value(self):
        for record in self:
            if record.duration_value <= 0:
                raise ValidationError('La durée doit être supérieure à zéro.')
