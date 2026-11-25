# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AmarnaClubInterventionPart(models.Model):
    """Spare part or consumable used on a ticket; leaves the stock when the
    ticket is closed (as the stock_maintenance bridge of Odoo)."""
    _name = 'amarna.club.intervention.part'
    _description = "Pièce utilisée sur une intervention"

    intervention_id = fields.Many2one(
        'amarna.club.intervention', string='Intervention', required=True, ondelete='cascade')
    item_id = fields.Many2one(
        'amarna.club.inventory.item', string='Article', required=True)
    qty = fields.Integer(string='Quantité', default=1, required=True)
    unit = fields.Char(related='item_id.unit')
    consumed = fields.Boolean(string='Sortie du stock', readonly=True, copy=False)

    _qty_positive = models.Constraint('check (qty > 0)', 'La quantité doit être positive.')

    @api.depends('item_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec.item_id.name or 'Pièce'


class AmarnaClubIntervention(models.Model):
    _inherit = 'amarna.club.intervention'

    part_ids = fields.One2many(
        'amarna.club.intervention.part', 'intervention_id', string='Pièces utilisées')

    def _on_resolved(self):
        super()._on_resolved()
        Move = self.env['amarna.club.inventory.move']
        for rec in self:
            for part in rec.part_ids.filtered(lambda p: not p.consumed):
                Move.create({
                    'item_id': part.item_id.id, 'move_type': 'out', 'reason': 'maintenance',
                    'qty': part.qty, 'notes': 'Intervention : %s' % rec.name})
                part.consumed = True
