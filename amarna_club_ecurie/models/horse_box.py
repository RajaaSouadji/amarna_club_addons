# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AmarnaClubHorseBox(models.Model):
    """Box or paddock of the stable, and the horses that sleep in it."""
    _name = 'amarna.club.horse.box'
    _description = "Box ou paddock"
    _order = 'name'

    name = fields.Char(string='Nom', required=True)
    kind = fields.Selection(
        [('box', 'Box'), ('paddock', 'Paddock')], string='Type', default='box', required=True)
    capacity = fields.Integer(string='Places', default=1)
    horse_ids = fields.One2many('amarna.club.horse', 'box_id', string='Chevaux')
    occupant_count = fields.Integer(compute='_compute_occupancy', store=True, string='Occupants')
    state = fields.Selection(
        [('free', 'Libre'), ('partial', 'Partiellement occupé'), ('full', 'Occupé')],
        compute='_compute_occupancy', store=True, string='État')
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _name_uniq = models.Constraint('unique (name)', 'Ce box existe déjà.')

    @api.constrains('capacity')
    def _check_capacity(self):
        for rec in self:
            if rec.capacity < 1:
                raise ValidationError("Un box doit avoir au moins une place.")

    @api.constrains('horse_ids', 'capacity')
    def _check_not_overbooked(self):
        for rec in self:
            if len(rec.horse_ids) > rec.capacity:
                raise ValidationError(
                    "%s accueille déjà %d cheval(aux) sur %d place(s)." % (
                        rec.name, len(rec.horse_ids), rec.capacity))

    @api.depends('horse_ids', 'capacity')
    def _compute_occupancy(self):
        for rec in self:
            rec.occupant_count = len(rec.horse_ids)
            if not rec.occupant_count:
                rec.state = 'free'
            elif rec.occupant_count >= rec.capacity:
                rec.state = 'full'
            else:
                rec.state = 'partial'
