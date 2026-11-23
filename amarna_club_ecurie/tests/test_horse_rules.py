# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
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
