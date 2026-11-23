# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AmarnaClubInventoryItem(models.Model):
    _name = 'amarna.club.inventory.item'
    _inherit = ['amarna.activity.mixin']
    _description = 'Consommable du club'
    _order = 'activity_id, name'

    name = fields.Char(required=True)

    code = fields.Char(
        string='Code mobile',
        index=True,
        copy=False,
        help="Identifiant du consommable dans l'application tablette "
             "(ex: inv-pool-01).",
    )


    qty = fields.Integer(string='Stock actuel', aggregator=None)

    low_threshold = fields.Integer(string='Seuil bas', aggregator=None)

    unit = fields.Char(
        string='Unité',
        help='ex: unités, kg, boîtes, seaux',
    )

    is_low = fields.Boolean(
        string='Stock bas',
        compute='_compute_is_low',
        store=True,
    )

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
