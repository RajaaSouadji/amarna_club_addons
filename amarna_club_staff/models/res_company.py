# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    amarna_staff_enforce_certifications = fields.Boolean(
        string='Exiger les certifications pour être affecté',
        help="Une personne ne peut être affectée à une activité que si elle détient, "
             "en cours de validité, les certifications que cette activité exige.")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    amarna_staff_enforce_certifications = fields.Boolean(
        related='company_id.amarna_staff_enforce_certifications', readonly=False)
