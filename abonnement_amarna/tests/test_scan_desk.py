# -*- coding: utf-8 -*-
"""Reader desk: one card read = one passage, with a guard against reading twice."""
from datetime import timedelta

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install', 'amarna')
class TestScanDesk(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.context_today(cls.env.user)
        cls.Checkin = cls.env['amarna.checkin']
        cls.gym = cls.env['amarna.club.activity'].search([('code', '=', 'gym')], limit=1)
        cls.gym.write({'mobile_status': 'open'})
        month = cls.env['amarna.subscription.type'].create({
            'name': 'Mensuel desk', 'duration_value': 1, 'duration_unit': 'month'})
        cls.plan = cls.env['amarna.subscription.plan'].create({
            'name': '5 séances desk', 'activity_id': cls.gym.id,
            'subscription_type_id': month.id, 'list_price': 0.0, 'session_count': 5})
        cls.member = cls.env['res.partner'].create({'name': 'Membre desk'})
        cls.card = cls.env['amarna.rfid.card'].create({'name': 'DESK-1', 'partner_id': cls.member.id})
        cls.sub = cls._confirmed_subscription(cls.member, cls.plan)

    @classmethod
    def _confirmed_subscription(cls, partner, plan):
        sub = cls.env['amarna.subscription'].create({
            'partner_id': partner.id, 'plan_id': plan.id, 'start_date': cls.today})
        sub.action_confirm()
        return sub

    def test_one_read_records_the_passage_and_takes_a_session(self):
        before = self.sub.remaining_sessions
        result = self.Checkin.scan_card('DESK-1')
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['member']['name'], 'Membre desk')
        self.assertEqual(self.sub.remaining_sessions, before - 1)
        self.assertEqual(self.Checkin.search_count([('subscription_id', '=', self.sub.id)]), 1)

    def test_reading_twice_in_a_row_takes_only_one_session(self):
        self.Checkin.scan_card('DESK-1')
        left = self.sub.remaining_sessions
        again = self.Checkin.scan_card('desk-1')            # the case of the number does not matter
        self.assertEqual(again['status'], 'duplicate')
        self.assertEqual(self.sub.remaining_sessions, left)
        self.assertEqual(self.Checkin.search_count([('subscription_id', '=', self.sub.id)]), 1)

    def test_the_guard_ends_after_its_delay_and_can_be_switched_off(self):
        self.Checkin.scan_card('DESK-1')
        self.Checkin.search([('subscription_id', '=', self.sub.id)]).checkin_datetime = (
            fields.Datetime.now() - timedelta(minutes=6))
        self.assertEqual(self.Checkin.scan_card('DESK-1')['status'], 'success')
        self.env.company.amarna_checkin_guard_minutes = 0
        self.assertEqual(self.Checkin.scan_card('DESK-1')['status'], 'success')
        self.assertEqual(self.sub.remaining_sessions, 5 - 3)

    def test_an_unknown_or_restricted_card_is_refused(self):
        self.assertEqual(self.Checkin.scan_card('NOPE')['status'], 'denied')
        self.assertEqual(self.Checkin.scan_card('')['status'], 'denied')
        self.card.action_lost()
        refused = self.Checkin.scan_card('DESK-1')
        self.assertEqual(refused['status'], 'denied')
        self.assertIn('perdue', refused['message'])
        self.assertEqual(self.sub.remaining_sessions, 5, 'a refused read takes nothing')

    def test_a_subscription_that_cannot_pay_is_refused_with_the_reason(self):
        paid_plan = self.plan.copy({'name': 'Payant desk', 'list_price': 100.0})
        other = self.env['res.partner'].create({'name': 'Membre impayé'})
        self.env['amarna.rfid.card'].create({'name': 'DESK-2', 'partner_id': other.id})
        sub = self._confirmed_subscription(other, paid_plan)
        result = self.Checkin.scan_card('DESK-2')
        self.assertEqual(result['status'], 'denied')
        self.assertIn('facture', result['message'].lower())
        self.assertEqual(sub.remaining_sessions, 5)

    def test_several_valid_subscriptions_ask_which_one(self):
        pool = self.env['amarna.club.activity'].search([('code', '!=', 'gym')], limit=1)
        pool.write({'mobile_status': 'open'})
        plan2 = self.plan.copy({'name': 'Autre activité desk', 'activity_id': pool.id})
        sub2 = self._confirmed_subscription(self.member, plan2)
        ask = self.Checkin.scan_card('DESK-1')
        self.assertEqual(ask['status'], 'choose')
        self.assertEqual({c['id'] for c in ask['choices']}, {self.sub.id, sub2.id})
        self.assertEqual(self.sub.remaining_sessions, 5, 'nothing is taken until a choice is made')
        done = self.Checkin.scan_card('DESK-1', subscription_id=sub2.id)
        self.assertEqual(done['status'], 'success')
        self.assertEqual(sub2.remaining_sessions, 4)
        self.assertEqual(self.sub.remaining_sessions, 5)

    def test_card_state_follows_the_access_and_only_lost_or_blocked_are_typed(self):
        self.card.invalidate_recordset()
        self.assertEqual(self.card.state, 'active', 'a paid, confirmed subscription opens the access')
        self.card.action_block()
        self.assertEqual(self.card.state, 'blocked')
        self.card.action_restore()
        self.assertEqual(self.card.state, 'active')
        self.sub.action_cancel()
        self.card.invalidate_recordset()
        self.assertEqual(self.card.state, 'inactive')
        self.assertNotIn('action_activate', dir(self.card), 'no button sets the access by hand')
