# -*- coding: utf-8 -*-
from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        """Open the home screen at login for every internal user.

        Odoo opens the action stored on the user (``action_id``); when a user
        has none it falls back to its first app. Doing it here, instead of
        writing ``action_id`` on each user, also covers users created later and
        keeps the choice of a user who picked another home action.
        """
        info = super().session_info()
        if info.get('is_internal_user') and not info.get('home_action_id'):
            home = self.env.ref('amarna_club_theme.action_amarna_home', raise_if_not_found=False)
            if home:
                info['home_action_id'] = home.id
        return info
