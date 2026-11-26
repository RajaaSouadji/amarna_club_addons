# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError

DEFAULT_BODY = (
    "Bonjour {name}, votre abonnement {plan} se termine le {date}. "
    "Passez à l'accueil pour le renouveler. {club}")


class ResCompany(models.Model):
    _inherit = 'res.company'

    amarna_sms_expiry_enabled = fields.Boolean(
        string="SMS avant la fin de l'abonnement", default=False,
        help="Désactivé par défaut. Une fois activé, un SMS part chaque matin vers les membres "
             "dont l'abonnement se termine dans le nombre de jours indiqué. Les SMS passent par "
             "le service SMS d'Odoo et consomment des crédits.")
    amarna_sms_expiry_days = fields.Integer(
        string="Envoyer … jours avant la fin", default=2,
        help="2 = le SMS part 48 heures avant la date de fin.")
    amarna_sms_expiry_body = fields.Text(
        string="Texte du SMS", default=DEFAULT_BODY,
        help="Mots remplacés : {name} le membre, {plan} la formule, {date} la date de fin, {club} le nom du club.")

    @api.constrains('amarna_sms_expiry_days')
    def _check_amarna_sms_days(self):
        for company in self:
            if company.amarna_sms_expiry_days < 0:
                raise ValidationError("Le nombre de jours avant la fin ne peut pas être négatif.")
