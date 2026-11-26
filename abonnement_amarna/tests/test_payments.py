# -*- coding: utf-8 -*-
"""Collecting at the desk: one button, a journal per payment method, the club cash list, reminders."""
from datetime import timedelta

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install', 'amarna')
class TestPayments(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.context_today(cls.env.user)
        cls.activity = cls.env['amarna.club.activity'].search([('code', '=', 'gym')], limit=1)
        cls.activity.write({'mobile_status': 'open'})
        month = cls.env['amarna.subscription.type'].create({
            'name': 'Mensuel paiement', 'duration_value': 1, 'duration_unit': 'month'})
        cls.plan = cls.env['amarna.subscription.plan'].create({
            'name': 'Forfait payant', 'activity_id': cls.activity.id,
            'subscription_type_id': month.id, 'list_price': 3000.0})
        cls.member = cls.env['res.partner'].create({'name': 'Membre paiement'})

    def _subscription(self):
        sub = self.env['amarna.subscription'].create({
            'partner_id': self.member.id, 'plan_id': self.plan.id, 'start_date': self.today,
            'user_id': self.env.user.id})
        sub.action_confirm()
        return sub

    def _pay(self, sub, journal):
        action = sub.action_collect()
        wizard = self.env['account.payment.register'].with_context(**action['context']).create(
            {'journal_id': journal.id})
        return wizard.action_create_payments()

    def test_there_is_a_journal_per_payment_method(self):
        codes = set(self.env['account.journal'].search([('company_id', '=', self.env.company.id)]).mapped('code'))
        self.assertTrue({'ESP', 'CHQ', 'CIB'} <= codes)
        # run again: nothing is created twice
        before = self.env['account.journal'].search_count([])
        self.env['account.journal']._amarna_ensure_payment_journals()
        self.assertEqual(self.env['account.journal'].search_count([]), before)

    def test_one_button_invoices_then_opens_the_payment_window(self):
        sub = self._subscription()
        self.assertEqual(sub.billing_state, 'to_invoice')
        action = sub.action_collect()
        self.assertEqual(sub.billing_state, 'unpaid', 'the period was invoiced by the same click')
        self.assertEqual(action['res_model'], 'account.payment.register')

    def test_a_cash_payment_opens_the_access_and_shows_in_the_club_list(self):
        sub = self._subscription()
        cash = self.env['account.journal'].search([('code', '=', 'ESP')], limit=1)
        self._pay(sub, cash)
        self.assertEqual(sub.billing_state, 'paid')
        payment = self.env['account.payment'].search([('amarna_club', '=', True), ('partner_id', '=', self.member.id)])
        self.assertEqual(len(payment), 1)
        self.assertEqual(payment.journal_id, cash)
        self.assertEqual(payment.amarna_activity_id, self.activity)
        self.assertEqual(payment.amount, 3000.0)

    def test_a_payment_of_something_else_is_not_a_club_payment(self):
        other = self.env['account.payment'].create({
            'partner_id': self.member.id, 'amount': 10.0, 'payment_type': 'inbound',
            'partner_type': 'customer', 'journal_id': self.env['account.journal'].search([('code', '=', 'CIB')], limit=1).id})
        self.assertFalse(other.amarna_club)

    def test_unpaid_invoices_are_chased_once_per_period(self):
        sub = self._subscription()
        sub.action_collect()
        invoice = sub.invoice_ids.filtered(lambda m: m.state == 'posted')
        self.env.company.amarna_payment_reminder_days = 7
        self.env['amarna.subscription'].cron_payment_reminders()
        self.assertFalse(sub.payment_reminder_date, 'not yet 7 days: no reminder')
        invoice.invoice_date_due = self.today - timedelta(days=8)
        self.env['amarna.subscription'].cron_payment_reminders()
        self.assertEqual(sub.payment_reminder_date, self.today)
        self.assertEqual(len(sub.activity_ids), 1)
        self.env['amarna.subscription'].cron_payment_reminders()
        self.assertEqual(len(sub.activity_ids), 1, 'not twice the same week')
        self.env.company.amarna_payment_reminder_days = 0
        sub.payment_reminder_date = False
        sub.activity_ids.unlink()
        self.env['amarna.subscription'].cron_payment_reminders()
        self.assertFalse(sub.activity_ids, '0 switches the reminder off')
