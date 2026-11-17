# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    """Pool water-quality rules, set by the club in Configuration > Piscine."""
    _inherit = 'res.company'

    amarna_pool_temp_min = fields.Float(string='Température minimale (°C)', default=26.0)
    amarna_pool_temp_max = fields.Float(string='Température maximale (°C)', default=30.0)
    amarna_pool_chlorine_min = fields.Float(string='Chlore minimum (mg/L)', default=1.0)
    amarna_pool_chlorine_max = fields.Float(string='Chlore maximum (mg/L)', default=3.0)
    amarna_pool_ph_min = fields.Float(string='pH minimum', default=7.2)
    amarna_pool_ph_max = fields.Float(string='pH maximum', default=7.6)
    amarna_pool_turbidity_max = fields.Float(string='Turbidité maximale (NTU)', default=1.0)
    amarna_pool_weight_temperature = fields.Integer(
        string='Points si température hors norme', default=20,
        help='Points retirés au score global quand ce paramètre est hors norme.')
    amarna_pool_weight_chlorine = fields.Integer(
        string='Points si chlore hors norme', default=30)
    amarna_pool_weight_ph = fields.Integer(
        string='Points si pH hors norme', default=30)
    amarna_pool_weight_turbidity = fields.Integer(
        string='Points si turbidité hors norme', default=20)

    @api.constrains('amarna_pool_temp_min', 'amarna_pool_temp_max',
                    'amarna_pool_chlorine_min', 'amarna_pool_chlorine_max',
                    'amarna_pool_ph_min', 'amarna_pool_ph_max')
    def _check_amarna_pool_ranges(self):
        for company in self:
            if (company.amarna_pool_temp_min > company.amarna_pool_temp_max
                    or company.amarna_pool_chlorine_min > company.amarna_pool_chlorine_max
                    or company.amarna_pool_ph_min > company.amarna_pool_ph_max):
                raise ValidationError('Le minimum de chaque plage doit être inférieur ou égal au maximum.')

    @api.constrains('amarna_pool_weight_temperature', 'amarna_pool_weight_chlorine',
                    'amarna_pool_weight_ph', 'amarna_pool_weight_turbidity')
    def _check_amarna_pool_weights(self):
        for company in self:
            weights = (company.amarna_pool_weight_temperature, company.amarna_pool_weight_chlorine,
                       company.amarna_pool_weight_ph, company.amarna_pool_weight_turbidity)
            if any(w < 0 for w in weights) or sum(weights) > 100:
                raise ValidationError('Les points des paramètres piscine doivent être positifs et totaliser au plus 100.')

    def write(self, vals):
        res = super().write(vals)
        if any(key.startswith('amarna_pool_') for key in vals):
            # Conformity is stored: recompute every reading against the new rules.
            self.env['amarna.club.pool.reading'].search([])._compute_conformity()
        return res

    def _amarna_app_config(self):
        config = super()._amarna_app_config()
        config['pool'] = {
            'temperature': {'min': self.amarna_pool_temp_min, 'max': self.amarna_pool_temp_max},
            'chlorine': {'min': self.amarna_pool_chlorine_min, 'max': self.amarna_pool_chlorine_max},
            'ph': {'min': self.amarna_pool_ph_min, 'max': self.amarna_pool_ph_max},
            'turbidity': {'max': self.amarna_pool_turbidity_max},
            'weights': {
                'temperature': self.amarna_pool_weight_temperature,
                'chlorine': self.amarna_pool_weight_chlorine,
                'ph': self.amarna_pool_weight_ph,
                'turbidity': self.amarna_pool_weight_turbidity,
            },
        }
        return config
