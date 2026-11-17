# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install', 'amarna')
class TestPoolRules(TransactionCase):

    def test_conformity_follows_the_club_settings(self):
        company = self.env.company
        company.write({
            'amarna_pool_chlorine_min': 1.0,
            'amarna_pool_chlorine_max': 3.0,
        })
        reading = self.env['amarna.club.pool.reading'].create({
            'temperature': 28.0, 'chlorine': 2.0, 'ph': 7.4, 'turbidity': 0.5,
        })
        self.assertTrue(reading.conform)
        self.assertAlmostEqual(reading.score, 100.0)

        # Tightening the club's chlorine ceiling must re-score stored readings.
        company.amarna_pool_chlorine_max = 1.5
        self.assertFalse(reading.chlorine_ok)
        self.assertEqual(reading.issue_count, 1)
        self.assertAlmostEqual(reading.score, 100.0 - company.amarna_pool_weight_chlorine)

    def test_weights_are_bounded(self):
        from odoo.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            self.env.company.amarna_pool_weight_chlorine = 90
