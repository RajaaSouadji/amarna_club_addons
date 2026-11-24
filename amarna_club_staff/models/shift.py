# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AmarnaClubShift(models.Model):
    """A guard slot: who works on which activity, and when."""
    _name = 'amarna.club.shift'
    _description = 'Garde du personnel'
    _order = 'start_at'

    staff_id = fields.Many2one(
        'amarna.club.staff', string='Personne', required=True, ondelete='cascade', index=True)
    activity_id = fields.Many2one('amarna.club.activity', string='Activité', required=True)
    start_at = fields.Datetime(string='Début', required=True, default=fields.Datetime.now)
    end_at = fields.Datetime(string='Fin', required=True)
    duration = fields.Float(string='Durée (h)', compute='_compute_duration', store=True)
    notes = fields.Char(string='Remarque')

    @api.depends('start_at', 'end_at')
    def _compute_duration(self):
        for rec in self:
            rec.duration = (
                (rec.end_at - rec.start_at).total_seconds() / 3600.0
                if rec.start_at and rec.end_at else 0.0)

    @api.constrains('start_at', 'end_at', 'staff_id')
    def _check_shift(self):
        for rec in self:
            if rec.end_at <= rec.start_at:
                raise ValidationError("La fin de la garde doit suivre son début.")
            overlap = self.search([
                ('id', '!=', rec.id), ('staff_id', '=', rec.staff_id.id),
                ('start_at', '<', rec.end_at), ('end_at', '>', rec.start_at)], limit=1)
            if overlap:
                raise ValidationError(
                    "%s a déjà une garde sur ce créneau (%s)." % (
                        rec.staff_id.name, overlap.activity_id.name))
