# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    """Armoury rules, set by the club in Configuration > Armurerie."""
    _inherit = 'res.company'

    amarna_weapon_cleaning_days = fields.Integer(
        string="Nettoyage des armes : intervalle (jours)", default=7,
        help="Une arme non nettoyée depuis plus de ce délai est signalée à nettoyer.")

    @api.constrains('amarna_weapon_cleaning_days')
    def _check_amarna_weapon_cleaning(self):
        for company in self:
            if company.amarna_weapon_cleaning_days < 1:
                raise ValidationError("L'intervalle de nettoyage doit être d'au moins 1 jour.")

    def _amarna_app_config(self):
        config = super()._amarna_app_config()
        config['armory'] = {
            'weapon_cleaning_days': self.amarna_weapon_cleaning_days,
        }
        return config
