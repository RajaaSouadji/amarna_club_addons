# -*- coding: utf-8 -*-
from odoo import api, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def _ensure_amarna_admin_access(self):
        """Ensure the Odoo administrator can see the Amarna Club apps."""
        admin = self.env.ref('base.user_admin', raise_if_not_found=False)
        club_user = self.env.ref(
            'abonnement_amarna.group_club_user',
            raise_if_not_found=False,
        )
        if admin and club_user:
            admin.sudo().write({'groups_id': [(4, club_user.id)]})