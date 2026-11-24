# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields, models
from odoo.exceptions import UserError, ValidationError


class AmarnaClubReservationRepeat(models.TransientModel):
    """Copy a booking on the following weeks ("every Tuesday at 18:00")."""
    _name = 'amarna.club.reservation.repeat'
    _description = 'Répéter une réservation chaque semaine'

    reservation_id = fields.Many2one(
        'amarna.club.reservation', string='Réservation', required=True, ondelete='cascade')
    weeks = fields.Integer(string='Nombre de semaines suivantes', default=4, required=True)
    result = fields.Text(string='Résultat', readonly=True)

    def action_repeat(self):
        self.ensure_one()
        if not 1 <= self.weeks <= 52:
            raise UserError("Choisissez entre 1 et 52 semaines.")
        source = self.reservation_id
        created, skipped = [], []
        for week in range(1, self.weeks + 1):
            day = source.reservation_date + timedelta(weeks=week)
            start_at, end_at = source._slot_datetimes(day, source.start_hour, source.end_hour)
            try:
                with self.env.cr.savepoint():
                    source.copy({'start_at': start_at, 'end_at': end_at, 'status': 'pending'})
                created.append(day)
            except ValidationError as error:
                skipped.append('%s : %s' % (day.strftime('%d/%m/%Y'), error.args[0]))
        lines = ['%d réservation(s) créée(s).' % len(created)]
        if skipped:
            lines.append('Non créées :')
            lines.extend(skipped)
        self.result = '\n'.join(lines)
        return {
            'type': 'ir.actions.act_window', 'res_model': self._name, 'res_id': self.id,
            'view_mode': 'form', 'target': 'new'}
