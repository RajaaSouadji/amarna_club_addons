# -*- coding: utf-8 -*-
"""Extension of the canonical reservation model (owned by ``abonnement_amarna``).

Adds what a booking desk needs beyond the core: the court/lane/instructor being
booked (with double-booking protection), weekly repetition, the waiting list
and the no-show / late-cancellation flags. The tablet never sends these
fields, so its flow is unchanged.
"""
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AmarnaClubReservation(models.Model):
    _inherit = 'amarna.club.reservation'

    resource_id = fields.Many2one(
        'amarna.club.resource', string='Terrain / ressource',
        domain="[('activity_id', '=', activity_id)]", tracking=True, index=True)
    no_show = fields.Boolean(string='Absent', copy=False, tracking=True)
    late_cancel = fields.Boolean(
        string='Annulation tardive', copy=False, readonly=True,
        help="Annulée moins de quelques heures avant le début (délai défini dans les paramètres).")

    # ------------------------------------------------------------ rules
    @api.constrains('resource_id', 'start_at', 'end_at', 'status', 'people_count')
    def _check_resource_free(self):
        for rec in self:
            if not rec.resource_id or rec.status == 'cancelled':
                continue
            others = self.search([
                ('id', '!=', rec.id), ('resource_id', '=', rec.resource_id.id),
                ('status', '!=', 'cancelled'),
                ('start_at', '<', rec.end_at), ('end_at', '>', rec.start_at)])
            if sum(others.mapped('people_count')) + rec.people_count > rec.resource_id.capacity:
                raise ValidationError(
                    "« %s » est déjà réservé(e) sur ce créneau (%d place(s) au total)." % (
                        rec.resource_id.name, rec.resource_id.capacity))

    @api.onchange('activity_id')
    def _onchange_activity_resource(self):
        if self.resource_id and self.resource_id.activity_id != self.activity_id:
            self.resource_id = False

    def write(self, vals):
        cancelling = self.browse()
        if vals.get('status') == 'cancelled':
            cancelling = self.filtered(lambda r: r.status != 'cancelled')
        result = super().write(vals)
        if cancelling:
            hours = self.env.company.amarna_reservation_late_cancel_hours
            now = fields.Datetime.now()
            for rec in cancelling:
                if hours and rec.start_at - now < timedelta(hours=hours):
                    rec.late_cancel = True
            self.env['amarna.club.reservation.waiting']._promote_for(cancelling)
        return result

    # ---------------------------------------------------------- buttons
    def action_no_show(self):
        for rec in self.filtered(lambda r: r.status in ('pending', 'confirmed')):
            rec.write({'no_show': True, 'status': 'cancelled'})

    def action_repeat(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': 'Répéter la réservation',
            'res_model': 'amarna.club.reservation.repeat', 'view_mode': 'form',
            'target': 'new', 'context': {'default_reservation_id': self.id}}
