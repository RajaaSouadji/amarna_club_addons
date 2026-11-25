# -*- coding: utf-8 -*-
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class AmarnaClubCertificationType(models.Model):
    """A qualification of the staff (lifeguard diploma, riding instructor, weapon
    licence...), like the skill types of Odoo HR."""
    _name = 'amarna.club.certification.type'
    _description = 'Type de certification'
    _order = 'name'

    name = fields.Char(string='Certification', required=True, translate=True)
    validity_months = fields.Integer(
        string='Validité (mois)', help="0 = sans date d'expiration.")
    role = fields.Selection(
        selection=lambda self: self.env['amarna.club.staff']._fields['role'].selection,
        string='Fonction concernée',
        help="Vide : concerne toutes les fonctions.")
    activity_ids = fields.Many2many(
        'amarna.club.activity', 'amarna_certification_activity_rel', 'type_id', 'activity_id',
        string='Exigée pour les activités',
        help="Vide : exigée pour toutes les activités (de la fonction concernée).")
    required = fields.Boolean(
        string='Obligatoire', default=True,
        help="Une certification facultative n'empêche jamais une affectation.")
    certification_count = fields.Integer(compute='_compute_certification_count')
    active = fields.Boolean(default=True)

    _name_uniq = models.Constraint('unique (name)', 'Ce type de certification existe déjà.')

    def _compute_certification_count(self):
        counts = dict(self.env['amarna.club.certification']._read_group(
            [('type_id', 'in', self.ids)], ['type_id'], ['__count']))
        for rec in self:
            rec.certification_count = counts.get(rec, 0)


class AmarnaClubCertification(models.Model):
    _name = 'amarna.club.certification'
    _inherit = ['mail.thread']
    _description = 'Certification du personnel'
    _order = 'date_end, id'

    staff_id = fields.Many2one(
        'amarna.club.staff', string='Personne', required=True, ondelete='cascade', index=True)
    type_id = fields.Many2one(
        'amarna.club.certification.type', string='Certification', required=True, tracking=True)
    reference = fields.Char(string='N° / référence')
    date_obtained = fields.Date(string='Obtenue le', default=fields.Date.context_today)
    date_end = fields.Date(
        string="Valable jusqu'au", compute='_compute_date_end', store=True, readonly=False,
        tracking=True, help="Calculée depuis la validité du type; modifiable.")
    document = fields.Binary(string='Justificatif', attachment=True)
    document_name = fields.Char()
    state = fields.Selection(
        [('valid', 'Valide'), ('expiring', 'Expire bientôt'),
         ('expired', 'Expirée'), ('permanent', 'Sans expiration')],
        string='État', compute='_compute_state')
    notes = fields.Text(string='Notes')

    @api.depends('date_obtained', 'type_id.validity_months')
    def _compute_date_end(self):
        for rec in self:
            months = rec.type_id.validity_months
            if rec.date_obtained and months:
                rec.date_end = rec.date_obtained + relativedelta(months=months)
            elif not months:
                rec.date_end = False

    @api.depends('date_end')
    def _compute_state(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if not rec.date_end:
                rec.state = 'permanent'
            elif rec.date_end < today:
                rec.state = 'expired'
            elif rec.date_end <= today + timedelta(days=60):
                rec.state = 'expiring'
            else:
                rec.state = 'valid'

    @api.depends('staff_id', 'type_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s – %s' % (
                rec.staff_id.display_name or 'Certification', rec.type_id.name or '')
