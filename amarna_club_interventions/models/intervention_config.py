# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AmarnaClubInterventionCategory(models.Model):
    """Kind of fault (electricity, plumbing...), as the categories of Odoo Maintenance."""
    _name = 'amarna.club.intervention.category'
    _description = "Catégorie d'intervention"
    _order = 'name'

    name = fields.Char(string='Catégorie', required=True, translate=True)
    color = fields.Integer(string='Couleur')
    staff_id = fields.Many2one(
        'amarna.club.staff', string='Technicien par défaut',
        help="Proposé automatiquement quand un ticket de cette catégorie est créé.")
    active = fields.Boolean(default=True)

    _name_uniq = models.Constraint('unique (name)', 'Cette catégorie existe déjà.')


class AmarnaClubInterventionTeam(models.Model):
    """Maintenance team: who can take a ticket of which activity."""
    _name = 'amarna.club.intervention.team'
    _description = "Équipe de maintenance"
    _order = 'name'

    name = fields.Char(string='Équipe', required=True)
    staff_ids = fields.Many2many(
        'amarna.club.staff', 'amarna_intervention_team_staff_rel',
        'team_id', 'staff_id', string='Membres')
    ticket_count = fields.Integer(compute='_compute_ticket_count', string='Tickets ouverts')
    active = fields.Boolean(default=True)

    def _compute_ticket_count(self):
        counts = dict(self.env['amarna.club.intervention']._read_group(
            [('team_id', 'in', self.ids), ('status', '!=', 'resolved')],
            ['team_id'], ['__count']))
        for rec in self:
            rec.ticket_count = counts.get(rec, 0)


class ResCompany(models.Model):
    _inherit = 'res.company'

    amarna_preventive_lead_days = fields.Integer(
        string='Entretien préventif : préavis (jours)', default=7,
        help="Un ticket d'entretien préventif est créé automatiquement "
             "ce nombre de jours avant la prochaine maintenance d'un équipement.")

    @api.constrains('amarna_preventive_lead_days')
    def _check_amarna_preventive_lead_days(self):
        for company in self:
            if company.amarna_preventive_lead_days < 0:
                raise ValidationError("Le préavis ne peut pas être négatif.")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    amarna_preventive_lead_days = fields.Integer(
        related='company_id.amarna_preventive_lead_days', readonly=False)
