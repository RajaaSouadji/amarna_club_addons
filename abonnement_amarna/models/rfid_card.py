# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AmarnaRfidCard(models.Model):
    _name = 'amarna.rfid.card'
    _description = 'Carte RFID membre'
    _order = 'name'

    name = fields.Char(string='Identifiant RFID', required=True, index=True)
    partner_id = fields.Many2one('res.partner', string='Membre', ondelete='set null', index=True)
    active = fields.Boolean(string='Carte active', default=False)
    state = fields.Selection([
        ('active', 'Active'), ('inactive', 'Inactive'), ('lost', 'Perdue'), ('blocked', 'Bloquée'),
    ], string='État', default='inactive', required=True)
    assigned_date = fields.Date(string='Date d’attribution', default=fields.Date.today)
    access_ids = fields.One2many('amarna.rfid.access', 'card_id', string='Autorisations d’accès', readonly=True)
    note = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)

    _sql_constraints = [
        ('rfid_name_unique', 'unique(name)', 'L’identifiant RFID doit être unique.'),
    ]

    @api.constrains('partner_id')
    def _check_one_card_per_member(self):
        for card in self.filtered('partner_id'):
            duplicate = self.search_count([('partner_id', '=', card.partner_id.id), ('id', '!=', card.id)])
            if duplicate:
                raise ValidationError('Un membre ne peut avoir qu’une seule carte RFID attribuée.')

    def _sync_access_state(self):
        now = fields.Datetime.now()
        for card in self:
            valid_access = card.access_ids.filtered(lambda access: access.active and access.state in ('scheduled', 'active') and access.start_datetime <= now <= access.end_datetime)
            if valid_access and card.state not in ('blocked', 'lost'):
                card.with_context(skip_rfid_sync=True).write({'active': True, 'state': 'active'})
            elif not valid_access and card.state == 'active':
                card.with_context(skip_rfid_sync=True).write({'active': False, 'state': 'inactive'})

    def action_activate(self):
        self.write({'state': 'active', 'active': True})

    def action_deactivate(self):
        self.write({'state': 'inactive', 'active': False})

    def action_block(self):
        self.write({'state': 'blocked', 'active': False})

    def action_unassign(self):
        self.write({'partner_id': False, 'state': 'inactive', 'active': False})


