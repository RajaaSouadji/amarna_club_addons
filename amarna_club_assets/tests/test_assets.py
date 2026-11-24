# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from odoo import fields
from odoo.exceptions import UserError
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


@tagged('post_install', '-at_install', 'amarna')
class TestAssetMaintenance(TransactionCase):
    """Categories, maintenance journal, contracts and armoury register."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Asset = cls.env['amarna.club.asset']
        cls.Service = cls.env['amarna.club.asset.service']
        cls.category = cls.env['amarna.club.asset.category'].create({
            'name': 'Machine test', 'maintenance_interval_days': 30})
        cls.asset = cls.Asset.create({
            'name': 'Tapis test', 'code': 'asset-test-treadmill',
            'mobile_activity_code': 'gym', 'category_id': cls.category.id})

    def test_category_fills_label_interval_and_staff(self):
        self.assertEqual(self.asset.category, 'Machine test')
        self.assertEqual(self.asset.maintenance_interval_days, 30)
        staff = self.env['amarna.club.staff'].create({'name': 'Tech test', 'role': 'technician'})
        self.category.staff_id = staff
        other = self.Asset.create({'name': 'Autre', 'category_id': self.category.id})
        self.assertEqual(other.staff_id, staff)

    def test_service_moves_last_and_next_maintenance(self):
        self.Service.create({
            'asset_id': self.asset.id, 'service_type': 'repair',
            'date': '2026-03-01', 'cost': 1500})
        self.assertEqual(self.asset.last_maintenance, datetime(2026, 3, 1))
        self.assertEqual(self.asset.next_maintenance, datetime(2026, 3, 31))
        self.assertEqual(self.asset.total_service_cost, 1500)
        self.assertEqual(self.asset.service_count, 1)

    def test_tablet_cleaning_creates_one_journal_line(self):
        weapon = self.Asset.create({
            'name': 'Arme test', 'code': 'asset-test-gun', 'is_weapon': True})
        weapon.write({'last_maintenance': datetime(2026, 4, 10, 15, 30)})
        service = self.Service.search([('asset_id', '=', weapon.id)])
        self.assertEqual(len(service), 1)
        self.assertEqual(service.service_type, 'cleaning')
        # Armoury rule: next cleaning = last + the company's cleaning interval.
        days = self.env.company.amarna_weapon_cleaning_days
        self.assertEqual(weapon.next_maintenance, datetime(2026, 4, 10) + timedelta(days=days))
        # The same day again does not duplicate the line.
        weapon.write({'last_maintenance': datetime(2026, 4, 10, 18, 0)})
        self.assertEqual(self.Service.search_count([('asset_id', '=', weapon.id)]), 1)

    def test_maintenance_due_filter(self):
        self.asset.next_maintenance = datetime.now() - timedelta(days=1)
        self.assertIn(self.asset, self.Asset.search([('maintenance_due', '=', True)]))
        self.assertNotIn(self.asset, self.Asset.search([('maintenance_due', '=', False)]))
        self.asset.next_maintenance = datetime.now() + timedelta(days=10)
        self.assertNotIn(self.asset, self.Asset.search([('maintenance_due', '=', True)]))

    def test_usage_counter_counts_each_start(self):
        self.asset.write({'status': 'inUse'})
        self.asset.write({'status': 'inUse'})   # already in use: not a new start
        self.asset.write({'status': 'available'})
        self.asset.write({'status': 'inUse'})
        self.assertEqual(self.asset.usage_count, 2)

    def test_contract_expiry_state(self):
        today = fields.Date.context_today(self.env.user)
        Contract = self.env['amarna.club.asset.contract']
        make = lambda end: Contract.create({
            'name': 'C', 'asset_id': self.asset.id, 'date_end': today + timedelta(days=end)})
        self.assertEqual(make(-1).expiry_state, 'expired')
        self.assertEqual(make(10).expiry_state, 'expiring')
        self.assertEqual(make(200).expiry_state, 'running')

    def test_weapon_register_follows_the_status(self):
        weapon = self.Asset.create({'name': 'Arme registre', 'is_weapon': True})
        member = self.env['res.partner'].create({'name': 'Tireur test'})
        log = self.env['amarna.club.weapon.log'].create({
            'asset_id': weapon.id, 'partner_id': member.id, 'ammo_issued': 25})
        self.assertEqual(weapon.status, 'inUse')
        self.assertEqual(weapon.weapon_state, 'issued')
        with self.assertRaises(UserError):
            self.env['amarna.club.weapon.log'].create({'asset_id': weapon.id})
        log.action_return()
        self.assertEqual(weapon.status, 'available')
        self.assertEqual(weapon.weapon_state, 'in_armory')
        self.assertTrue(log.returned_at)
