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


@tagged('post_install', '-at_install', 'amarna')
class TestPoolOperations(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pool = cls.env['amarna.club.activity'].search([('code', '=', 'pool')], limit=1)
        cls.Reading = cls.env['amarna.club.pool.reading']

    def _reading(self, chlorine):
        return self.Reading.create({
            'temperature': 28.0, 'chlorine': chlorine, 'ph': 7.4, 'turbidity': 0.5})

    def test_task_due_date_and_state_follow_the_last_execution(self):
        from datetime import timedelta
        from odoo import fields
        Task = self.env['amarna.club.pool.task']
        task = Task.create({'name': 'Contre-lavage test', 'interval_days': 7})
        today = fields.Date.context_today(self.env.user)
        self.assertEqual(task.next_due, today + timedelta(days=7))
        self.assertEqual(task.state, 'ok')
        task.next_due = today - timedelta(days=1)
        self.assertEqual(task.state, 'late')
        self.assertIn(task, Task.search([('state', '=', 'late')]))
        self.assertNotIn(task, Task.search([('state', '=', 'ok')]))
        task.action_done()
        self.assertEqual(task.last_done, today)
        self.assertEqual(task.next_due, today + timedelta(days=7))
        self.assertEqual(task.state, 'ok')
        self.assertEqual(len(task.log_ids), 1)

    def test_lifeguard_ratio_uses_the_club_limit(self):
        company = self.env.company
        company.amarna_pool_max_bathers_per_lifeguard = 20
        self.pool.staff_ids = False
        self.pool.current_occupancy = 30
        self.assertFalse(self.pool.lifeguard_ratio_ok)       # nobody watching
        guards = self.env['amarna.club.staff'].create([
            {'name': 'MNS test 1', 'role': 'lifeguard', 'activity_ids': [(6, 0, self.pool.ids)]}])
        self.pool.invalidate_recordset()
        self.assertEqual(self.pool.lifeguard_count, 1)
        self.assertFalse(self.pool.lifeguard_ratio_ok)       # 30 per guard > 20
        self.env['amarna.club.staff'].create({
            'name': 'MNS test 2', 'role': 'lifeguard', 'activity_ids': [(6, 0, self.pool.ids)]})
        self.pool.invalidate_recordset()
        self.assertTrue(self.pool.lifeguard_ratio_ok)        # 15 per guard
        self.pool.current_occupancy = 0
        self.assertTrue(self.pool.lifeguard_ratio_ok)

    def test_bad_reading_closes_the_pool_only_when_enabled(self):
        self.pool.write({'mobile_status': 'open', 'pool_auto_closed': False})
        self.env.company.amarna_pool_auto_close = False
        self._reading(chlorine=9.0)
        self.assertEqual(self.pool.mobile_status, 'open')
        self.env.company.amarna_pool_auto_close = True
        self._reading(chlorine=9.0)
        self.assertEqual(self.pool.mobile_status, 'closed')
        self.assertTrue(self.pool.pool_auto_closed)
        self.assertTrue(self.pool.closure_start)

    def test_good_reading_reopens_only_an_automatic_closure(self):
        self.env.company.amarna_pool_auto_close = True
        self.pool.write({'mobile_status': 'closed', 'pool_auto_closed': False})
        self._reading(chlorine=2.0)
        self.assertEqual(self.pool.mobile_status, 'closed')   # closed by hand: stays closed
        self.pool.write({'mobile_status': 'open'})
        self._reading(chlorine=9.0)
        self.assertEqual(self.pool.mobile_status, 'closed')
        self._reading(chlorine=2.0)
        self.assertEqual(self.pool.mobile_status, 'open')
        self.assertFalse(self.pool.pool_auto_closed)

    def test_incident_can_be_closed_and_reopened(self):
        incident = self.env['amarna.club.pool.incident'].create({'name': 'Glissade'})
        self.assertEqual(incident.state, 'open')
        incident.action_close()
        self.assertEqual(incident.state, 'closed')
        incident.action_reopen()
        self.assertEqual(incident.state, 'open')
