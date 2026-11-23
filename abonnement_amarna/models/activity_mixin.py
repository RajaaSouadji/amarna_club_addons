# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AmarnaActivityMixin(models.AbstractModel):
    """Link a record to a club activity from the code the tablet sends.

    The tablet knows activities by their code ("pool", "padel"...), the back
    office links them with a normal Many2one. Writing `mobile_activity_code`
    resolves `activity_id`; both stay editable.
    """
    _name = 'amarna.activity.mixin'
    _description = "Rattachement à une activité du club"

    mobile_activity_code = fields.Char(
        string='Code activité mobile',
        index=True,
        help="Code d'activité envoyé par la tablette; le lien Activité "
             "est résolu automatiquement.",
    )
    activity_id = fields.Many2one(
        'amarna.club.activity',
        string='Activité',
        compute='_compute_activity_id',
        store=True,
        readonly=False,
        index=True,
    )

    @api.depends('mobile_activity_code')
    def _compute_activity_id(self):
        Activity = self.env['amarna.club.activity']
        for rec in self:
            if rec.mobile_activity_code:
                rec.activity_id = Activity._find_by_mobile_code(rec.mobile_activity_code)
            elif not rec.activity_id:
                rec.activity_id = False
