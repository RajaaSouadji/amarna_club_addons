# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    """Horse care rules, set by the club in Configuration > Écurie."""
    _inherit = 'res.company'

    amarna_horse_fatigue_alert = fields.Float(
        string="Seuil d'alerte de fatigue (0 à 1)", default=0.7,
        help="Au-delà de ce niveau, la fatigue du cheval est affichée en alerte.")
    amarna_horse_fatigue_rested = fields.Float(
        string="Seuil « reposé » (0 à 1)", default=0.3,
        help="En dessous de ce niveau, le cheval est affiché comme reposé.")
    amarna_farrier_interval_days = fields.Integer(
        string='Ferrage : intervalle (jours)', default=42,
        help='Un ferrage plus ancien que ce délai est signalé « à prévoir ».')
    amarna_deworming_interval_days = fields.Integer(
        string='Vermifuge : intervalle (jours)', default=90,
        help='Un vermifuge plus ancien que ce délai est signalé « à prévoir ».')

    @api.constrains('amarna_horse_fatigue_alert', 'amarna_horse_fatigue_rested')
    def _check_amarna_fatigue_alert(self):
        for company in self:
            alert, rested = company.amarna_horse_fatigue_alert, company.amarna_horse_fatigue_rested
            if not (0.0 <= rested <= alert <= 1.0):
                raise ValidationError(
                    "Les seuils de fatigue doivent être compris entre 0 et 1, "
                    "le seuil « reposé » ne dépassant pas le seuil d'alerte.")

    @api.constrains('amarna_farrier_interval_days', 'amarna_deworming_interval_days')
    def _check_amarna_care_intervals(self):
        for company in self:
            if company.amarna_farrier_interval_days <= 0 or company.amarna_deworming_interval_days <= 0:
                raise ValidationError("Les intervalles de soins doivent être supérieurs à zéro.")

    def _amarna_app_config(self):
        config = super()._amarna_app_config()
        config['horses'] = {
            'fatigue_alert': self.amarna_horse_fatigue_alert,
            'fatigue_rested': self.amarna_horse_fatigue_rested,
            'farrier_interval_days': self.amarna_farrier_interval_days,
            'deworming_interval_days': self.amarna_deworming_interval_days,
        }
        return config
