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

CLUB_MODULES = {
    'abonnement_amarna', 'amarna_club_reservations', 'amarna_club_assets',
    'amarna_club_interventions', 'amarna_club_inventory', 'amarna_club_ecurie',
    'amarna_club_pool', 'amarna_club_staff',
}


@odoo.tests.tagged('post_install', '-at_install', 'amarna_ui', '-standard')
class TestAmarnaWebClient(odoo.tests.HttpCase):
    allow_end_on_form = True

    def test_every_screen_of_every_club_app_opens(self):
        self.env.ref('base.user_admin').tour_enabled = False
        roots = self.env['ir.ui.menu'].search([('parent_id', '=', False)])
        xmlids = sorted(
            xmlid for xmlid in (root.get_external_id().get(root.id) for root in roots)
            if xmlid and xmlid.split('.')[0] in CLUB_MODULES)
        self.assertGreaterEqual(len(xmlids), 2, 'Aucune application du club trouvée')
        for xmlid in xmlids:
            with self.subTest(app=xmlid):
                self.browser_js(
                    '/odoo',
                    "odoo.loader.modules.get('@web/webclient/clickbot/clickbot_loader')"
                    ".startClickEverywhere({ xmlId: '%s', logger: true });" % xmlid,
                    'odoo.isReady === true',
                    login='admin', timeout=1200,
                    success_signal='clickbot test succeeded')
