# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AmarnaClubResource(models.Model):
    """Something that is booked: a padel court, a pool lane, a paintball
    field, an instructor. Its capacity is the number of people it can host
    at the same time (1 for a court booked as a whole)."""
    _name = 'amarna.club.resource'
    _description = 'Ressource réservable'
    _order = 'activity_id, name'

    name = fields.Char(string='Ressource', required=True)
    activity_id = fields.Many2one(
        'amarna.club.activity', string='Activité', required=True, ondelete='cascade')
    capacity = fields.Integer(
        string='Capacité simultanée', default=1, required=True,
        help="Nombre de personnes pouvant réserver en même temps. 1 = réservable une seule fois par créneau.")
    notes = fields.Text(string='Notes')
    color = fields.Integer(string='Couleur')
    reservation_count = fields.Integer(compute='_compute_reservation_count', string='Réservations à venir')
    active = fields.Boolean(default=True)

    @api.constrains('capacity')
    def _check_capacity(self):
        for rec in self:
            if rec.capacity < 1:
                raise ValidationError("La capacité doit être d'au moins 1.")

    def _compute_reservation_count(self):
        now = fields.Datetime.now()
        counts = dict(self.env['amarna.club.reservation']._read_group(
            [('resource_id', 'in', self.ids), ('status', '!=', 'cancelled'),
             ('end_at', '>', now)], ['resource_id'], ['__count']))
        for rec in self:
            rec.reservation_count = counts.get(rec, 0)

    def action_view_reservations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': 'Réservations',
            'res_model': 'amarna.club.reservation', 'view_mode': 'calendar,list,form',
            'domain': [('resource_id', '=', self.id)],
            'context': {'default_resource_id': self.id,
                        'default_activity_id': self.activity_id.id}}
