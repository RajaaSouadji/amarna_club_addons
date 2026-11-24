# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AmarnaClubInventoryLocation(models.Model):
    """Storage place of the club (bar, armoury, stable, pool room...)."""
    _name = 'amarna.club.inventory.location'
    _description = 'Emplacement de stock'
    _order = 'name'

    name = fields.Char(string='Emplacement', required=True)
    activity_id = fields.Many2one('amarna.club.activity', string='Activité')
    item_count = fields.Integer(compute='_compute_item_count', string='Articles')
    active = fields.Boolean(default=True)

    _name_uniq = models.Constraint('unique (name)', 'Cet emplacement existe déjà.')

    def _compute_item_count(self):
        counts = dict(self.env['amarna.club.inventory.item']._read_group(
            [('location_id', 'in', self.ids)], ['location_id'], ['__count']))
        for rec in self:
            rec.item_count = counts.get(rec, 0)


class AmarnaClubInventoryItem(models.Model):
    _name = 'amarna.club.inventory.item'
    _inherit = ['mail.thread', 'amarna.activity.mixin']
    _description = 'Consommable du club'
    _order = 'activity_id, name'

    name = fields.Char(required=True, tracking=True)

    code = fields.Char(
        string='Code mobile',
        index=True,
        copy=False,
        help="Identifiant du consommable dans l'application tablette "
             "(ex: inv-pool-01).",
    )

    # The tablet writes the absolute quantity; every change is journaled.
    qty = fields.Integer(string='Stock actuel', aggregator=None)

    low_threshold = fields.Integer(string='Seuil bas', aggregator=None, tracking=True)

    unit = fields.Char(
        string='Unité',
        help='ex: unités, kg, boîtes, seaux',
    )

    is_low = fields.Boolean(
        string='Stock bas',
        compute='_compute_is_low',
        store=True,
    )

    location_id = fields.Many2one('amarna.club.inventory.location', string='Emplacement')
    supplier_id = fields.Many2one('res.partner', string='Fournisseur habituel')
    reorder_qty = fields.Integer(
        string='Quantité à commander',
        help="Quantité habituellement commandée quand le stock est bas.")
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)
    unit_cost = fields.Monetary(string='Coût unitaire', currency_field='currency_id')
    stock_value = fields.Monetary(
        string='Valeur du stock', compute='_compute_stock_value',
        currency_field='currency_id')
    to_order_qty = fields.Integer(
        string='À commander', compute='_compute_to_order_qty',
        help="Quantité conseillée pour revenir au-dessus du seuil.")
    move_ids = fields.One2many('amarna.club.inventory.move', 'item_id', string='Mouvements')
    move_count = fields.Integer(compute='_compute_move_count')
    notes = fields.Text(string='Notes')

    active = fields.Boolean(default=True)

    @api.constrains('qty', 'low_threshold')
    def _check_quantities(self):
        for rec in self:
            if rec.qty < 0:
                raise ValidationError(
                    'Le stock de « %s » ne peut pas être négatif.' % rec.name)
            if rec.low_threshold < 0:
                raise ValidationError(
                    'Le seuil bas de « %s » ne peut pas être négatif.' % rec.name)

    @api.depends('qty', 'low_threshold')
    def _compute_is_low(self):
        for rec in self:
            rec.is_low = rec.qty <= rec.low_threshold

    @api.depends('qty', 'unit_cost')
    def _compute_stock_value(self):
        for rec in self:
            rec.stock_value = rec.qty * rec.unit_cost

    @api.depends('qty', 'low_threshold', 'reorder_qty')
    def _compute_to_order_qty(self):
        for rec in self:
            if rec.qty > rec.low_threshold:
                rec.to_order_qty = 0
            else:
                rec.to_order_qty = rec.reorder_qty or (rec.low_threshold - rec.qty + 1)

    def _compute_move_count(self):
        counts = dict(self.env['amarna.club.inventory.move']._read_group(
            [('item_id', 'in', self.ids)], ['item_id'], ['__count']))
        for rec in self:
            rec.move_count = counts.get(rec, 0)

    # ----------------------------------------------------------- journal
    def write(self, vals):
        """A quantity typed in Odoo or pushed by the tablet becomes an
        adjustment line, so the stock history never has holes."""
        if 'qty' not in vals or self.env.context.get('amarna_stock_move'):
            return super().write(vals)
        before = {rec.id: rec.qty for rec in self}
        result = super().write(vals)
        moves = []
        for rec in self:
            delta = rec.qty - before[rec.id]
            if delta:
                moves.append({
                    'item_id': rec.id, 'move_type': 'adjust', 'reason': 'correction',
                    'qty': delta, 'notes': 'Quantité modifiée (fiche ou tablette)',
                    'applied': True})
        if moves:
            self.env['amarna.club.inventory.move'].with_context(
                amarna_stock_move=True).create(moves)
        return result

    def action_view_moves(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': 'Mouvements de stock',
            'res_model': 'amarna.club.inventory.move', 'view_mode': 'list,form',
            'domain': [('item_id', '=', self.id)],
            'context': {'default_item_id': self.id},
        }

    def _action_new_move(self, move_type, reason):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': 'Mouvement de stock',
            'res_model': 'amarna.club.inventory.move', 'view_mode': 'form',
            'target': 'new',
            'context': {'default_item_id': self.id, 'default_move_type': move_type,
                        'default_reason': reason},
        }

    def action_stock_in(self):
        return self._action_new_move('in', 'purchase')

    def action_stock_out(self):
        return self._action_new_move('out', 'consumption')
