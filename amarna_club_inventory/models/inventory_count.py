# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class AmarnaClubInventoryCount(models.Model):
    """Physical stock count: compare shelves with the system, then adjust."""
    _name = 'amarna.club.inventory.count'
    _inherit = ['mail.thread']
    _description = 'Inventaire physique'
    _order = 'date desc, id desc'

    name = fields.Char(string='Référence', required=True, copy=False, default='Nouveau')
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    location_id = fields.Many2one(
        'amarna.club.inventory.location', string='Emplacement',
        help="Laisser vide pour compter tous les articles.")
    user_id = fields.Many2one('res.users', string='Responsable', default=lambda self: self.env.user)
    state = fields.Selection(
        [('draft', 'Brouillon'), ('done', 'Validé')],
        default='draft', required=True, tracking=True, copy=False)
    line_ids = fields.One2many('amarna.club.inventory.count.line', 'count_id', string='Lignes')
    difference_count = fields.Integer(compute='_compute_difference_count', string='Écarts')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'amarna.club.inventory.count') or 'Nouveau'
        return super().create(vals_list)

    @api.depends('line_ids.difference')
    def _compute_difference_count(self):
        for rec in self:
            rec.difference_count = len(rec.line_ids.filtered('difference'))

    def action_load_items(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError("Cet inventaire est déjà validé.")
            domain = [('id', 'not in', rec.line_ids.item_id.ids)]
            if rec.location_id:
                domain.append(('location_id', '=', rec.location_id.id))
            items = self.env['amarna.club.inventory.item'].search(domain)
            rec.write({'line_ids': [(0, 0, {
                'item_id': item.id, 'theoretical_qty': item.qty,
                'counted_qty': item.qty}) for item in items]})

    def action_validate(self):
        Move = self.env['amarna.club.inventory.move']
        for rec in self:
            if rec.state != 'draft':
                continue
            for line in rec.line_ids.filtered('difference'):
                # Compare with the quantity now in the system: sales may have
                # moved it since the line was loaded.
                delta = line.counted_qty - line.item_id.qty
                if delta:
                    Move.create({
                        'item_id': line.item_id.id, 'move_type': 'adjust',
                        'reason': 'count', 'qty': delta,
                        'notes': rec.name})
            rec.state = 'done'


class AmarnaClubInventoryCountLine(models.Model):
    _name = 'amarna.club.inventory.count.line'
    _description = "Ligne d'inventaire physique"

    count_id = fields.Many2one(
        'amarna.club.inventory.count', required=True, ondelete='cascade')
    item_id = fields.Many2one(
        'amarna.club.inventory.item', string='Article', required=True)
    unit = fields.Char(related='item_id.unit')
    theoretical_qty = fields.Integer(string='Théorique', readonly=True)
    counted_qty = fields.Integer(string='Compté')
    difference = fields.Integer(string='Écart', compute='_compute_difference', store=True)

    @api.depends('theoretical_qty', 'counted_qty')
    def _compute_difference(self):
        for rec in self:
            rec.difference = rec.counted_qty - rec.theoretical_qty

    _item_uniq = models.Constraint(
        'unique (count_id, item_id)', 'Un article ne peut apparaître qu\'une fois par inventaire.')

    @api.depends('count_id', 'item_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s – %s' % (rec.count_id.name or 'Inventaire', rec.item_id.name or '')
