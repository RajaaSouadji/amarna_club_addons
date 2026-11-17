# -*- coding: utf-8 -*-
"""Club settings: taxes live on the records, hours and delays are validated,
and the tablet receives the configured values instead of its own copies."""
from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install', 'amarna')
class TestAmarnaConfig(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env['res.partner'].create({'name': 'Membre config'})
        cls.tax_10 = cls.env['account.tax'].create({
            'name': 'TVA test 10 %', 'amount': 10.0, 'amount_type': 'percent',
            'type_tax_use': 'sale', 'company_id': cls.company.id,
        })
        cls.tax_20 = cls.env['account.tax'].create({
            'name': 'TVA test 20 %', 'amount': 20.0, 'amount_type': 'percent',
            'type_tax_use': 'sale', 'company_id': cls.company.id,
        })
        cls.activity = cls.env['amarna.club.activity'].search([('code', '=', 'gym')], limit=1)
        cls.activity.write({'unit_price': 20.0, 'mobile_status': 'open'})
        cls.sub_type = cls.env['amarna.subscription.type'].create({
            'name': 'Mensuel config', 'duration_value': 1, 'duration_unit': 'month',
        })

    def _plan(self, **extra):
        vals = {
            'name': 'Forfait config',
            'activity_id': self.activity.id,
            'subscription_type_id': self.sub_type.id,
            'list_price': 100.0,
            'session_count': 0,
        }
        vals.update(extra)
        return self.env['amarna.subscription.plan'].create(vals)

    def _reservation(self, **extra):
        vals = {
            'activity_id': self.activity.id,
            'mobile_activity_code': self.activity.code,
            'partner_id': self.partner.id,
            'client_name': 'Membre config',
            'reservation_date': fields.Date.context_today(self.env.user) + timedelta(days=2),
            'start_hour': 10.0,
            'end_hour': 11.0,
            'people_count': 2,
        }
        vals.update(extra)
        return self.env['amarna.club.reservation'].create(vals)

    def test_new_activity_and_plan_take_the_company_default_tax(self):
        self.company.amarna_default_tax_id = self.tax_10
        activity = self.env['amarna.club.activity'].create({
            'name': 'Activité test TVA', 'code': 'tva-test',
        })
        plan = self._plan()
        self.assertEqual(activity.tax_ids, self.tax_10)
        self.assertEqual(plan.tax_ids, self.tax_10)

    def test_reservation_is_taxed_with_its_activity_tax(self):
        self.activity.tax_ids = self.tax_10
        resa = self._reservation()
        self.assertAlmostEqual(resa.amount_untaxed, 40.0)
        self.assertAlmostEqual(resa.amount_total, 44.0)

    def test_changing_the_activity_tax_changes_the_amount(self):
        self.activity.tax_ids = self.tax_10
        resa = self._reservation()
        self.activity.tax_ids = self.tax_20
        self.assertAlmostEqual(resa.amount_total, 48.0)

    def test_subscription_is_taxed_with_its_plan_tax_not_the_product(self):
        plan = self._plan(tax_ids=[(6, 0, self.tax_20.ids)])
        sub = self.env['amarna.subscription'].create({
            'partner_id': self.partner.id, 'plan_id': plan.id,
        })
        sub.action_confirm()
        self.assertAlmostEqual(sub.amount_untaxed, 100.0)
        self.assertAlmostEqual(sub.amount_total, 120.0)

    def test_closing_hour_must_follow_opening_hour(self):
        with self.assertRaises(ValidationError):
            self.company.amarna_closing_hour = self.company.amarna_opening_hour - 1

    def test_default_slot_must_be_valid(self):
        with self.assertRaises(ValidationError):
            self.company.amarna_default_end_hour = self.company.amarna_default_start_hour

    def test_negative_delays_are_refused(self):
        with self.assertRaises(ValidationError):
            self.company.amarna_ticket_due_days = -1

    def test_new_reservation_uses_the_configured_default_slot(self):
        self.company.write({
            'amarna_default_start_hour': 14.5,
            'amarna_default_end_hour': 16.0,
        })
        resa = self.env['amarna.club.reservation'].with_company(self.company).new({
            'activity_id': self.activity.id,
        })
        self.assertAlmostEqual(resa.start_hour, 14.5)
        self.assertAlmostEqual(resa.end_hour, 16.0)

    def test_app_config_exposes_company_settings(self):
        self.company.write({
            'amarna_default_tax_id': self.tax_20.id,
            'amarna_expiry_warning_days': 14,
            'amarna_ticket_due_days': 5,
            'amarna_support_phone': '0000000000',
        })
        config = self.env['res.company'].amarna_app_config(self.company.id)
        self.assertEqual(config['tax']['id'], self.tax_20.id)
        self.assertAlmostEqual(config['tax']['rate'], 20.0)
        self.assertEqual(config['subscriptions']['expiry_warning_days'], 14)
        self.assertEqual(config['tickets']['due_days'], 5)
        self.assertEqual(config['support']['phone'], '0000000000')
        self.assertIn('opening_hour', config['club'])
        self.assertIn('symbol', config['currency'])
        self.assertIn('horizon_days', config['reservations'])
        self.assertIn('default_people_count', config['reservations'])

    def test_app_config_without_tax_is_null_not_zero(self):
        self.company.amarna_default_tax_id = False
        config = self.env['res.company'].amarna_app_config(self.company.id)
        self.assertIsNone(config['tax']['id'])
        self.assertIsNone(config['tax']['rate'])

    def test_staff_list_only_holds_club_staff(self):
        staff = self.env['amarna.club.staff'].create({
            'name': 'Technicien test', 'role': 'technician',
        })
        self.assertTrue(staff.active)
        self.assertEqual(staff.company_id, self.company)

    def test_app_config_exposes_report_periods(self):
        self.company.write({
            'amarna_report_period_days': '7, 14,30',
            'amarna_report_default_days': 14,
        })
        config = self.env['res.company'].amarna_app_config(self.company.id)
        self.assertEqual(config['reports']['period_days'], [7, 14, 30])
        self.assertEqual(config['reports']['default_days'], 14)

    def test_default_report_period_must_be_listed(self):
        with self.assertRaises(ValidationError):
            self.company.amarna_report_default_days = 99

    def test_report_periods_must_be_numbers(self):
        with self.assertRaises(ValidationError):
            self.company.amarna_report_period_days = 'sept,trente'

    def test_my_profile_returns_the_staff_card_of_the_user(self):
        self.env['amarna.club.staff'].create({
            'name': 'Technicien profil', 'role': 'technician',
            'user_id': self.env.user.id,
            'activity_ids': [(6, 0, self.activity.ids)],
        })
        profile = self.env['amarna.club.staff'].amarna_my_profile()
        self.assertEqual(profile['name'], 'Technicien profil')
        self.assertEqual(profile['role'], 'Technicien')
        self.assertEqual([a['code'] for a in profile['activities']], [self.activity.code])

    def test_my_profile_is_empty_without_a_staff_card(self):
        user = self.env['res.users'].create({'name': 'Sans fiche', 'login': 'sans_fiche_test'})
        self.assertEqual(self.env['amarna.club.staff'].with_user(user).amarna_my_profile(), {})

    def test_activities_carry_their_tablet_screen(self):
        gym = self.env['amarna.club.activity'].search([('code', '=', 'gym')], limit=1)
        self.assertEqual(gym.mobile_screen, 'gym')
