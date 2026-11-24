# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install', 'amarna')
class TestHorseRules(TransactionCase):

    def test_rested_threshold_cannot_exceed_the_alert_threshold(self):
        company = self.env.company
        company.write({'amarna_horse_fatigue_rested': 0.2, 'amarna_horse_fatigue_alert': 0.8})
        with self.assertRaises(ValidationError):
            company.amarna_horse_fatigue_rested = 0.9

    def test_config_exposes_the_horse_rules(self):
        company = self.env.company
        company.write({'amarna_horse_fatigue_rested': 0.25, 'amarna_horse_fatigue_alert': 0.75})
        config = self.env['res.company'].amarna_app_config(company.id)
        self.assertEqual(config['horses']['fatigue_rested'], 0.25)
        self.assertEqual(config['horses']['fatigue_alert'], 0.75)

    def test_farrier_due_follows_the_club_interval(self):
        horse = self.env['amarna.club.horse'].create({
            'name': 'Cheval test', 'code': 'horse-test-rules',
            'last_farrier': fields.Date.context_today(self.env.user) - timedelta(days=50),
        })
        self.env.company.amarna_farrier_interval_days = 42
        self.assertTrue(horse.farrier_due)
        self.env.company.amarna_farrier_interval_days = 60
        horse.invalidate_recordset(['farrier_due'])
        self.assertFalse(horse.farrier_due)

    def test_care_due_filters_search_the_same_rule(self):
        Horse = self.env['amarna.club.horse']
        horse = Horse.create({
            'name': 'Cheval filtre', 'code': 'horse-test-filter',
            'last_farrier': fields.Date.context_today(self.env.user) - timedelta(days=50),
        })
        self.env.company.amarna_farrier_interval_days = 42
        self.assertIn(horse, Horse.search([('farrier_due', '=', True)]))
        self.assertNotIn(horse, Horse.search([('farrier_due', '=', False)]))
        self.assertNotIn(horse, Horse.search([('farrier_due', '!=', True)]))
        self.env.company.amarna_farrier_interval_days = 60
        self.assertNotIn(horse, Horse.search([('farrier_due', '=', True)]))
        self.assertIn(horse, Horse.search([('farrier_due', '=', False)]))


@tagged('post_install', '-at_install', 'amarna')
class TestStableManagement(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Horse = cls.env['amarna.club.horse']
        cls.horse = cls.Horse.create({'name': 'Cheval soins', 'code': 'horse-test-care'})
        cls.today = fields.Date.context_today(cls.env.user)

    def _care(self, care_type, days_ago, **vals):
        return self.env['amarna.club.horse.care'].create(dict(
            vals, horse_id=self.horse.id, care_type=care_type,
            date=self.today - timedelta(days=days_ago)))

    def test_care_journal_feeds_the_last_dates(self):
        self._care('farrier', 60)
        self._care('farrier', 10)
        self._care('vaccine', 100)
        self._care('deworming', 5)
        self.assertEqual(self.horse.last_farrier, self.today - timedelta(days=10))
        self.assertEqual(self.horse.last_vaccine, self.today - timedelta(days=100))
        self.assertEqual(self.horse.last_deworming, self.today - timedelta(days=5))
        self.assertFalse(self.horse.farrier_due)
        self.assertEqual(self.horse.care_count, 4)

    def test_date_typed_without_journal_is_kept(self):
        self.horse.last_farrier = self.today - timedelta(days=80)
        self.assertTrue(self.horse.farrier_due)
        self._care('vet', 2)    # another kind of care must not erase it
        self.assertEqual(self.horse.last_farrier, self.today - timedelta(days=80))

    def test_vet_visit_sets_the_next_visit(self):
        self._care('vet', 0, next_due=self.today + timedelta(days=30))
        self.assertEqual(self.horse.next_vet_visit.date(), self.today + timedelta(days=30))

    def test_age_follows_the_birth_date_and_stays_writable(self):
        self.horse.age = 9
        self.assertEqual(self.horse.age, 9)
        self.horse.birth_date = self.today.replace(year=self.today.year - 6) - timedelta(days=1)
        self.assertEqual(self.horse.age, 6)

    def test_box_label_and_capacity(self):
        box = self.env['amarna.club.horse.box'].create({'name': 'Box test 1'})
        self.horse.box_id = box
        self.assertEqual(self.horse.box_number, 'Box test 1')
        self.assertEqual(box.state, 'full')
        other = self.Horse.create({'name': 'Intrus', 'code': 'horse-test-intrus'})
        with self.assertRaises(ValidationError):
            other.box_id = box
        paddock = self.env['amarna.club.horse.box'].create({
            'name': 'Paddock test', 'kind': 'paddock', 'capacity': 2})
        (self.horse | other).box_id = paddock
        self.assertEqual(paddock.state, 'full')

    def test_feeding_plan_builds_the_diet_text(self):
        self.env['amarna.club.horse.feed'].create([
            {'horse_id': self.horse.id, 'meal': 'morning', 'feed_name': 'Foin', 'quantity': 3},
            {'horse_id': self.horse.id, 'meal': 'evening', 'feed_name': 'Granulés', 'quantity': 1.5},
        ])
        self.assertEqual(self.horse.diet, 'Matin : Foin 3 kg ; Soir : Granulés 1.5 kg')

    def test_boarding_contract_invoices_the_owner_once_a_month(self):
        owner = self.env['res.partner'].create({'name': 'Propriétaire test'})
        contract = self.env['amarna.club.horse.boarding'].create({
            'horse_id': self.horse.id, 'owner_id': owner.id, 'monthly_fee': 30000})
        with self.assertRaises(UserError):
            contract.action_invoice_month()      # not started yet
        contract.action_start()
        self.assertTrue(self.horse.is_boarder)
        self.assertEqual(self.horse.owner_id, owner)
        contract.action_invoice_month()
        invoice = contract.invoice_ids
        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.partner_id, owner)
        self.assertEqual(invoice.amount_untaxed, 30000)
        with self.assertRaises(UserError):
            contract.action_invoice_month()      # same month twice
