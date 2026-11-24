# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    amarna_reservation_late_cancel_hours = fields.Integer(
        string='Annulation tardive : délai (heures)', default=2,
        help="Une réservation annulée moins de ce nombre d'heures avant son début "
             "est marquée « annulation tardive ». 0 = pas de suivi.")

    @api.constrains('amarna_reservation_late_cancel_hours')
    def _check_amarna_late_cancel_hours(self):
        for company in self:
            if company.amarna_reservation_late_cancel_hours < 0:
                raise ValidationError("Le délai d'annulation ne peut pas être négatif.")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    amarna_reservation_late_cancel_hours = fields.Integer(
        related='company_id.amarna_reservation_late_cancel_hours', readonly=False)
