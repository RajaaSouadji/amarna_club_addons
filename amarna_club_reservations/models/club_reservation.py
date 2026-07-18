# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AmarnaClubReservation(models.Model):
    _name = 'amarna.club.reservation'
    _description = 'Réservation du club'
    _order = 'start_at desc'

    name = fields.Char(
        string='Titre',
        required=True,
        help='La tablette envoie "Activité - Client".',
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

    client_name = fields.Char(string='Client')

    partner_id = fields.Many2one(
        'res.partner',
        string='Contact',
        help='Lien optionnel vers un contact Odoo.',
    )

    people_count = fields.Integer(string='Personnes', default=1)

    start_at = fields.Datetime(string='Début', required=True)

    end_at = fields.Datetime(string='Fin', required=True)

    # Raw status written by the tablet ("Confirme", "En attente",
    # "Annule", "checkedin"); free text on purpose.
    status = fields.Char(
        string='Statut (brut)',
        default='En attente',
    )

    status_normalized = fields.Selection(
        [
            ('pending', 'En attente'),
            ('confirmed', 'Confirmé'),
            ('checked_in', 'Arrivé'),
            ('cancelled', 'Annulé'),
            ('unknown', 'Inconnu'),
        ],
        string='Statut',
        compute='_compute_status_normalized',
        store=True,
    )

    notes = fields.Text(string='Notes')

    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
    )

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

    @api.depends('status')
    def _compute_status_normalized(self):
        # Mirrors the parsing rules of the mobile app
        # (odoo_reservation_service.dart::_parseStatus).
        for rec in self:
            value = (rec.status or '').lower()
            if not value:
                rec.status_normalized = False
            elif 'check' in value or 'arriv' in value:
                rec.status_normalized = 'checked_in'
            elif 'confirm' in value:
                rec.status_normalized = 'confirmed'
            elif 'attente' in value or 'pending' in value:
                rec.status_normalized = 'pending'
            elif 'cancel' in value or 'annul' in value:
                rec.status_normalized = 'cancelled'
            else:
                rec.status_normalized = 'unknown'

    def action_check_in(self):
        """Check-in from the Odoo UI; also bumps activity occupancy,
        matching the tablet behaviour."""
        for rec in self:
            rec.status = 'checkedin'
            if rec.activity_id:
                occupancy = (rec.activity_id.current_occupancy
                             + max(rec.people_count, 1))
                if rec.activity_id.max_capacity:
                    occupancy = min(occupancy, rec.activity_id.max_capacity)
                rec.activity_id.current_occupancy = occupancy

    def action_cancel(self):
        self.write({'status': 'Annule'})
