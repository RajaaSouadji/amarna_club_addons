# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install', 'amarna')
class TestAssetsAndCheckpoints(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.padel = cls.env['amarna.club.activity'].search([('code', '=', 'padel')], limit=1)
        cls.court = cls.env['amarna.club.asset'].create({
            'name': 'Terrain test', 'code': 'asset-test-court',
            'mobile_activity_code': 'padel', 'status': 'available',
        })

    def test_in_use_since_follows_the_status(self):
        self.assertFalse(self.court.in_use_since)
        self.court.write({'status': 'inUse'})
        started = self.court.in_use_since
        self.assertTrue(started)
        # Writing inUse again keeps the original start time.
        self.court.write({'status': 'inUse'})
        self.assertEqual(self.court.in_use_since, started)
        self.court.write({'status': 'available'})
        self.assertFalse(self.court.in_use_since)

    def test_created_in_use_gets_a_start_time(self):
        court = self.env['amarna.club.asset'].create({
            'name': 'Terrain en cours', 'code': 'asset-test-court-2',
            'mobile_activity_code': 'padel', 'status': 'inUse',
        })
        self.assertTrue(court.in_use_since)

    def test_weapon_flag_is_set_by_the_admin_not_guessed_from_the_category(self):
        asset = self.env['amarna.club.asset'].create({
            'name': 'Arme sans drapeau', 'code': 'asset-test-weapon',
            'category': 'Arme de poing', 'mobile_activity_code': 'shooting',
        })
        self.assertFalse(asset.is_weapon)
        asset.is_weapon = True
        self.assertTrue(asset.is_weapon)

    def test_checkpoint_records_when_it_was_checked(self):
        point = self.env['amarna.club.checkpoint'].create({
            'name': 'Filets test', 'activity_id': self.padel.id,
        })
        self.assertTrue(point.is_ok)
        self.assertFalse(point.last_checked)
        point.is_ok = False
        self.assertTrue(point.last_checked)
        self.assertEqual(point.mobile_activity_code, 'padel')
