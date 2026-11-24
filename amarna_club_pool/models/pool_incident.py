# -*- coding: utf-8 -*-
from odoo import fields, models


class AmarnaClubPoolIncident(models.Model):
    """Accident book of the pool: every incident, rescue or complaint."""
    _name = 'amarna.club.pool.incident'
    _inherit = ['mail.thread']
    _description = 'Incident de la piscine'
    _order = 'date desc, id desc'

    name = fields.Char(string='Résumé', required=True, tracking=True)
    date = fields.Datetime(string='Date et heure', required=True, default=fields.Datetime.now)
    incident_type = fields.Selection([
        ('injury', 'Blessure'),
        ('rescue', 'Sauvetage / noyade évitée'),
        ('illness', 'Malaise'),
        ('behaviour', 'Comportement / règlement'),
        ('water', "Problème d'eau (produit, hygiène)"),
        ('other', 'Autre'),
    ], string='Nature', default='injury', required=True, tracking=True)
    severity = fields.Selection([
        ('minor', 'Mineur'), ('moderate', 'Modéré'), ('serious', 'Grave'),
    ], string='Gravité', default='minor', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Personne concernée')
    staff_id = fields.Many2one('amarna.club.staff', string='Maître-nageur présent')
    description = fields.Text(string='Ce qui s\'est passé')
    action_taken = fields.Text(string='Mesures prises')
    emergency_called = fields.Boolean(string='Secours appelés')
    state = fields.Selection(
        [('open', 'Ouvert'), ('closed', 'Clos')],
        default='open', required=True, tracking=True, copy=False)

    def action_close(self):
        self.write({'state': 'closed'})

    def action_reopen(self):
        self.write({'state': 'open'})
