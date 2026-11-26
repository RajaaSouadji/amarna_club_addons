# -*- coding: utf-8 -*-
import json

from odoo.tests import HttpCase, new_test_user, tagged


@tagged('amarna', 'post_install', '-at_install')
class TestSessionInfo(HttpCase):
    """What the web client receives at login."""

    def test_home_screen_and_no_onboarding_tour(self):
        user = new_test_user(self.env, login='theme_tester', groups='base.group_user')
        user.tour_enabled = True  # as for a real new user
        self.authenticate('theme_tester', 'theme_tester')
        response = self.url_open(
            '/web/session/get_session_info',
            data=json.dumps({'jsonrpc': '2.0', 'method': 'call', 'params': {}}),
            headers={'Content-Type': 'application/json'},
        )
        info = response.json()['result']
        home = self.env.ref('amarna_club_theme.action_amarna_home')
        self.assertEqual(info['home_action_id'], home.id)
        self.assertFalse(info.get('tour_enabled'), 'no onboarding tour at login')
        self.assertFalse(info.get('current_tour'))
