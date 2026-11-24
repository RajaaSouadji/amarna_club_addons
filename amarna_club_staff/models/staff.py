# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AmarnaClubStaff(models.Model):
    _inherit = 'amarna.club.staff'

    image_1920 = fields.Image(string='Photo', max_width=1024, max_height=1024)
    email = fields.Char(string='E-mail')
    hire_date = fields.Date(string="Date d'embauche")
    certification_ids = fields.One2many(
        'amarna.club.certification', 'staff_id', string='Certifications')
    shift_ids = fields.One2many('amarna.club.shift', 'staff_id', string='Gardes')
    expired_certification_count = fields.Integer(
        string='Certifications expirées', compute='_compute_certification_alerts')
    expiring_certification_count = fields.Integer(
        string='Certifications à renouveler', compute='_compute_certification_alerts')

    @api.depends('certification_ids.state')
    def _compute_certification_alerts(self):
        for rec in self:
            states = rec.certification_ids.mapped('state')
            rec.expired_certification_count = states.count('expired')
            rec.expiring_certification_count = states.count('expiring')

    def _missing_certifications(self, activity):
        """Required certification types this person lacks (or holds expired)
        to work on `activity`."""
        self.ensure_one()
        today = fields.Date.context_today(self)
        required = self.env['amarna.club.certification.type'].search([
            ('required', '=', True),
            '|', ('role', '=', False), ('role', '=', self.role),
            '|', ('activity_ids', '=', False), ('activity_ids', 'in', activity.ids)])
        held = self.certification_ids.filtered(
            lambda c: not c.date_end or c.date_end >= today).type_id
        return required - held

    @api.constrains('activity_ids', 'role', 'active')
    def _check_required_certifications(self):
        for rec in self:
            if not rec.active or not rec.company_id.amarna_staff_enforce_certifications:
                continue
            for activity in rec.activity_ids:
                missing = rec._missing_certifications(activity)
                if missing:
                    raise ValidationError(
                        "%s ne peut pas être affecté(e) à « %s » : certification manquante ou "
                        "expirée (%s)." % (rec.name, activity.name, ', '.join(missing.mapped('name'))))
