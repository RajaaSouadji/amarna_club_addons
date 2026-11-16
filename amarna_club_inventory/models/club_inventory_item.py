# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AmarnaClubInventoryItem(models.Model):
    _name = 'amarna.club.inventory.item'
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

    mobile_activity_code = fields.Char(
        string='Code activité mobile',
    )

    activity_id = fields.Many2one(
        'amarna.club.activity',
        string='Activité',
        compute='_compute_activity_id',
        store=True,
        readonly=False,
    )

    qty = fields.Integer(string='Stock actuel')

    low_threshold = fields.Integer(string='Seuil bas')

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

    @api.depends('mobile_activity_code')
    def _compute_activity_id(self):
        Activity = self.env['amarna.club.activity']
        for rec in self:
            if rec.mobile_activity_code:
                rec.activity_id = Activity._find_by_mobile_code(
                    rec.mobile_activity_code
                )
            elif not rec.activity_id:
                rec.activity_id = False

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
