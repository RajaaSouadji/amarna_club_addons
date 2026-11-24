# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models


class AmarnaClubAssetContract(models.Model):
    """Warranty, maintenance contract or licence of an equipment, with its
    expiry date (as the contracts of Odoo Fleet)."""
    _name = 'amarna.club.asset.contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Contrat / garantie d'équipement"
    _order = 'date_end'

    name = fields.Char(string='Référence', required=True, tracking=True)
    asset_id = fields.Many2one(
        'amarna.club.asset', string='Équipement', required=True,
        ondelete='cascade', index=True)
    contract_type = fields.Selection([
        ('warranty', 'Garantie'),
        ('maintenance', "Contrat d'entretien"),
        ('insurance', 'Assurance'),
        ('licence', 'Licence / autorisation'),
    ], string='Type', required=True, default='warranty', tracking=True)
    supplier_id = fields.Many2one('res.partner', string='Fournisseur')
    date_start = fields.Date(string='Début', default=fields.Date.context_today)
    date_end = fields.Date(string='Fin', required=True, tracking=True)
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)
    cost = fields.Monetary(string='Coût', currency_field='currency_id')
    notes = fields.Text(string='Notes')
    expiry_state = fields.Selection([
        ('running', 'En cours'),
        ('expiring', 'Expire bientôt'),
        ('expired', 'Expiré'),
    ], string='Échéance', compute='_compute_expiry_state')
    active = fields.Boolean(default=True)

    @api.depends('date_end')
    def _compute_expiry_state(self):
        today = fields.Date.context_today(self)
        soon = today + timedelta(days=30)
        for rec in self:
            if not rec.date_end or rec.date_end >= soon:
                rec.expiry_state = 'running'
            elif rec.date_end >= today:
                rec.expiry_state = 'expiring'
            else:
                rec.expiry_state = 'expired'
