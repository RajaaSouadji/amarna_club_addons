# -*- coding: utf-8 -*-
"""Job roles decide which apps a person sees; every role keeps the rights of the tablet user."""
from odoo.tests import new_test_user, tagged
from odoo.tests.common import TransactionCase

P = 'abonnement_amarna.'
# role -> apps (root menus) it must see; the ones it must not see are the others of ALL_APPS
ALL_APPS = {
    'menu_amarna_root': P,
    'menu_club_reservations_root': 'amarna_club_reservations.',
    'menu_club_assets_root': 'amarna_club_assets.',
    'menu_club_interventions_root': 'amarna_club_interventions.',
    'menu_club_inventory_root': 'amarna_club_inventory.',
    'menu_club_ecurie_root': 'amarna_club_ecurie.',
    'menu_club_pool_root': 'amarna_club_pool.',
    'menu_club_staff_root': 'amarna_club_staff.',
}
EXPECTED = {
    'group_club_user': set(),
    'group_club_reception': {'menu_amarna_root', 'menu_club_reservations_root', 'menu_club_interventions_root'},
    'group_club_coach': {'menu_amarna_root', 'menu_club_reservations_root', 'menu_club_assets_root',
                         'menu_club_interventions_root', 'menu_club_ecurie_root', 'menu_club_pool_root'},
    'group_club_technician': {'menu_club_assets_root', 'menu_club_interventions_root',
                              'menu_club_inventory_root', 'menu_club_pool_root'},
    'group_club_manager': set(ALL_APPS),
}


@tagged('post_install', '-at_install', 'amarna')
class TestRoles(TransactionCase):

    def _visible_apps(self, group_xmlid):
        user = new_test_user(self.env, login='role_' + group_xmlid, groups='base.group_user,' + P + group_xmlid)
        visible_ids = self.env['ir.ui.menu'].with_user(user)._visible_menu_ids()
        visible = set()
        for key, prefix in ALL_APPS.items():
            menu = self.env.ref(prefix + key, raise_if_not_found=False)
            if menu and menu.id in visible_ids:
                visible.add(key)
        return visible

    def test_each_role_sees_its_apps_and_only_those(self):
        installed = {k for k, prefix in ALL_APPS.items() if self.env.ref(prefix + k, raise_if_not_found=False)}
        for group, expected in EXPECTED.items():
            with self.subTest(role=group):
                self.assertEqual(self._visible_apps(group), expected & installed)

    def test_every_role_implies_the_tablet_user_and_the_manager_implies_all(self):
        user_group = self.env.ref(P + 'group_club_user')
        for group in ('group_club_reception', 'group_club_coach', 'group_club_technician', 'group_club_manager'):
            self.assertIn(user_group, self.env.ref(P + group).all_implied_ids, group)
        manager = self.env.ref(P + 'group_club_manager')
        for group in ('group_club_reception', 'group_club_coach', 'group_club_technician'):
            self.assertIn(self.env.ref(P + group), manager.all_implied_ids)

    def test_a_role_can_still_do_the_daily_work(self):
        """The ACL are those of the tablet user: a coach checks a member in, reception collects."""
        user = new_test_user(self.env, login='role_coach_work', groups='base.group_user,' + P + 'group_club_coach')
        Subscription = self.env['amarna.subscription'].with_user(user)
        self.assertTrue(Subscription.has_access('read'))
        self.assertTrue(self.env['amarna.checkin'].with_user(user).has_access('create'))
        self.assertFalse(self.env['amarna.subscription.plan'].with_user(user).has_access('write'),
                         'the catalogue stays for the manager')
