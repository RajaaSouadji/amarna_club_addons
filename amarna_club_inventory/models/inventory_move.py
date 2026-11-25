# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError

MOVE_TYPES = [('in', 'Entrée'), ('out', 'Sortie'), ('adjust', 'Ajustement')]
MOVE_REASONS = [
    ('purchase', 'Achat / réception'),
    ('consumption', 'Consommation'),
    ('loss', 'Perte / casse'),
    ('maintenance', 'Maintenance'),
    ('count', 'Inventaire physique'),
    ('correction', 'Correction'),
]


class AmarnaClubInventoryMove(models.Model):
    """Stock ledger: every change of a consumable's quantity, with who and why."""
    _name = 'amarna.club.inventory.move'
    _description = 'Mouvement de stock'
    _order = 'date desc, id desc'

    item_id = fields.Many2one(
        'amarna.club.inventory.item', string='Article', required=True,
        ondelete='cascade', index=True)
    activity_id = fields.Many2one(related='item_id.activity_id', store=True)
    location_id = fields.Many2one(related='item_id.location_id', store=True)
    date = fields.Datetime(string='Date', required=True, default=fields.Datetime.now)
    move_type = fields.Selection(MOVE_TYPES, string='Type', required=True, default='in')
    reason = fields.Selection(MOVE_REASONS, string='Motif', required=True, default='purchase')
    qty = fields.Integer(
        string='Quantité', required=True,
        help="Toujours positive pour une entrée ou une sortie; "
             "signée pour un ajustement (+ ou -).")
    qty_delta = fields.Integer(
        string='Variation', compute='_compute_qty_delta', store=True)
    user_id = fields.Many2one(
        'res.users', string='Utilisateur', default=lambda self: self.env.user)
    notes = fields.Char(string='Remarque')
    applied = fields.Boolean(
        default=False, copy=False,
        help="Technique : la quantité de l'article a déjà été mise à jour.")

    @api.depends('move_type', 'qty')
    def _compute_qty_delta(self):
        for rec in self:
            if rec.move_type == 'out':
                rec.qty_delta = -abs(rec.qty)
            elif rec.move_type == 'in':
                rec.qty_delta = abs(rec.qty)
            else:
                rec.qty_delta = rec.qty

    @api.model_create_multi
    def create(self, vals_list):
        # `applied` is set at creation so that users, who may create but not
        # modify a ledger line, never need write access on it.
        pending = [not vals.get('applied') for vals in vals_list]
        vals_list = [dict(vals, applied=True) for vals in vals_list]
        moves = super().create(vals_list)
        for move, to_apply in zip(moves, pending):
            if to_apply:
                move.item_id.with_context(amarna_stock_move=True).qty += move.qty_delta
        return moves

    def write(self, vals):
        locked = {'item_id', 'move_type', 'qty', 'date'}
        if locked & set(vals) and any(rec.applied for rec in self):
            raise UserError(
                "Un mouvement enregistré ne se modifie pas : créez un ajustement.")
        return super().write(vals)

    def unlink(self):
        if not self.env.su and not self.env.context.get('force_move_delete'):
            raise UserError("Les mouvements de stock ne se suppriment pas : créez un ajustement.")
        return super().unlink()

    @api.depends('item_id', 'qty_delta')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s (%+d)' % (rec.item_id.name or 'Mouvement', rec.qty_delta or 0)
