# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AmarnaClubCheckpoint(models.Model):
    """Control point checked before a session, e.g. nets or inflatables.

    The admin defines the points of each activity; the tablet lists them,
    and a point that blocks the session prevents starting one until fixed.
    """
    _name = 'amarna.club.checkpoint'
    _description = 'Point de contrôle avant session'
    _order = 'activity_id, sequence, id'

    name = fields.Char(string='Point de contrôle', required=True)
    activity_id = fields.Many2one(
        'amarna.club.activity', string='Activité', required=True, ondelete='cascade')
    mobile_activity_code = fields.Char(
        related='activity_id.code', store=True, string='Code activité')
    sequence = fields.Integer(default=10)
    is_ok = fields.Boolean(
        string='Conforme', default=True,
        help="État actuel, mis à jour depuis la tablette.")
    blocks_session = fields.Boolean(
        string='Bloque la session', default=True,
        help="Si ce point n'est pas conforme, aucune session ne peut démarrer.")
    last_checked = fields.Datetime(string='Dernier contrôle', readonly=True, copy=False)
    active = fields.Boolean(default=True)

    def write(self, vals):
        if 'is_ok' in vals and 'last_checked' not in vals:
            vals = dict(vals, last_checked=fields.Datetime.now())
        return super().write(vals)
