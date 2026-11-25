# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class AmarnaClubReservationWaiting(models.Model):
    """Waiting list: someone wants a slot that is full. When a booking is
    cancelled the first matching entry is promoted into a real reservation."""
    _name = 'amarna.club.reservation.waiting'
    _inherit = ['mail.thread']
    _description = "Liste d'attente de réservation"
    _order = 'create_date, id'

    partner_id = fields.Many2one('res.partner', string='Membre / client', required=True, tracking=True)
    activity_id = fields.Many2one('amarna.club.activity', string='Activité', required=True)
    resource_id = fields.Many2one(
        'amarna.club.resource', string='Terrain / ressource',
        domain="[('activity_id', '=', activity_id)]")
    reservation_date = fields.Date(string='Date', required=True)
    start_hour = fields.Float(string='De', required=True)
    end_hour = fields.Float(string='À', required=True)
    people_count = fields.Integer(string='Personnes', default=1)
    state = fields.Selection(
        [('waiting', 'En attente'), ('promoted', 'Réservé'), ('cancelled', 'Annulé')],
        default='waiting', required=True, tracking=True, copy=False)
    reservation_id = fields.Many2one(
        'amarna.club.reservation', string='Réservation créée', readonly=True, copy=False)

    @api.constrains('start_hour', 'end_hour')
    def _check_hours(self):
        for rec in self:
            if rec.end_hour <= rec.start_hour:
                raise ValidationError("L'heure de fin doit suivre l'heure de début.")

    def _reservation_vals(self):
        self.ensure_one()
        return {
            'activity_id': self.activity_id.id, 'resource_id': self.resource_id.id,
            'partner_id': self.partner_id.id, 'client_name': self.partner_id.name,
            'reservation_date': self.reservation_date,
            'start_hour': self.start_hour, 'end_hour': self.end_hour,
            'people_count': self.people_count}

    def action_promote(self):
        """Create the reservation now; fails loudly if the slot is still full."""
        for rec in self:
            if rec.state != 'waiting':
                raise UserError("Cette demande n'est plus en attente.")
            reservation = self.env['amarna.club.reservation'].create(rec._reservation_vals())
            rec.write({'state': 'promoted', 'reservation_id': reservation.id})
            rec.message_post(body="Une place s'est libérée : réservation <b>%s</b> créée." % reservation.name)

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    @api.model
    def _promote_for(self, cancelled):
        """After a cancellation, offer the freed slot to the waiting list."""
        for booking in cancelled:
            day = booking.reservation_date
            waiting = self.search([
                ('state', '=', 'waiting'), ('activity_id', '=', booking.activity_id.id),
                ('reservation_date', '=', day),
                ('start_hour', '<', booking.end_hour), ('end_hour', '>', booking.start_hour)])
            for entry in waiting:
                try:
                    with self.env.cr.savepoint():
                        entry.action_promote()
                except (ValidationError, UserError):
                    continue
                break

    @api.depends('partner_id', 'activity_id', 'reservation_date')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s – %s' % (
                rec.partner_id.name or 'Attente', rec.activity_id.name or '')
