# -*- coding: utf-8 -*-
"""Open every screen of the Amarna Club app in a real (headless) Chrome.

Server-side tests cannot see web-client errors (a view arch the browser does
not accept, a missing kanban template...). Odoo's "clickbot" opens every menu,
every view type and the first records, and fails on any console error.

Slow and needs Chrome, so it is NOT part of the default `amarna` tag:
    odoo-bin -d <seeded db> -u abonnement_amarna --test-enable --test-tags amarna_ui
Run it on a database filled by tools/seed_demo.py so there are records to open.
"""
import odoo.tests


@odoo.tests.tagged('post_install', '-at_install', 'amarna_ui', '-standard')
class TestAmarnaWebClient(odoo.tests.HttpCase):
    allow_end_on_form = True

    def test_every_screen_of_the_club_app_opens(self):
        root = self.env.ref('abonnement_amarna.menu_amarna_root')
        self.env.ref('base.user_admin').tour_enabled = False
        self.browser_js(
            '/odoo',
            "odoo.loader.modules.get('@web/webclient/clickbot/clickbot_loader')"
            ".startClickEverywhere({ xmlId: '%s', logger: true });" % root.get_external_id()[root.id],
            'odoo.isReady === true',
            login='admin', timeout=1200,
            success_signal='clickbot test succeeded')
