# -*- coding: utf-8 -*-
"""The end-of-subscription SMS: off by default, once per end date, never without a number."""
from datetime import timedelta

from odoo import fields
from odoo.addons.sms.tests.common import SMSCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'amarna')
class TestExpirySms(SMSCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.context_today(cls.env.user)
        activity = cls.env['amarna.club.activity'].search([('code', '=', 'gym')], limit=1)
        activity.write({'mobile_status': 'open'})
        month = cls.env['amarna.subscription.type'].create({
            'name': 'Mensuel sms', 'duration_value': 1, 'duration_unit': 'month'})
        cls.plan = cls.env['amarna.subscription.plan'].create({
            'name': 'Forfait SMS', 'activity_id': activity.id,
            'subscription_type_id': month.id, 'list_price': 0.0})
        cls.member = cls.env['res.partner'].create({'name': 'Membre SMS', 'phone': '+213 555 12 34 56'})

    def _ending_in(self, days, partner=None):
        sub = self.env['amarna.subscription'].create({
            'partner_id': (partner or self.member).id, 'plan_id': self.plan.id,
            'start_date': self.today - timedelta(days=20)})
        sub.action_confirm()
        sub.expiration_date = self.today + timedelta(days=days)
        return sub

    def test_it_is_off_by_default(self):
        self.assertFalse(self.env.company.amarna_sms_expiry_enabled)
        self._ending_in(2)
        with self.mockSMSGateway():
            self.env['amarna.subscription'].cron_expiry_sms()
        self.assertFalse(self._new_sms)

    def test_a_sms_goes_two_days_before_the_end_and_only_once(self):
        self.env.company.amarna_sms_expiry_enabled = True
        sub = self._ending_in(2)
        too_early = self._ending_in(3, self.env['res.partner'].create({'name': 'Trop tôt', 'phone': '+213 555 00 00 01'}))
        with self.mockSMSGateway():
            self.env['amarna.subscription'].cron_expiry_sms()
        self.assertEqual(len(self._new_sms), 1)
        self.assertIn('Membre SMS', self._new_sms.body)
        self.assertIn((self.today + timedelta(days=2)).strftime('%d/%m/%Y'), self._new_sms.body)
        self.assertEqual(sub.expiry_sms_for, sub.expiration_date)
        self.assertFalse(too_early.expiry_sms_for)
        with self.mockSMSGateway():
            self.env['amarna.subscription'].cron_expiry_sms()
        self.assertFalse(self._new_sms, 'the second run sends nothing')
        # renewed: a new end date arms the next SMS
        sub.expiration_date = self.today + timedelta(days=2, hours=0)
        sub.expiry_sms_for = False
        with self.mockSMSGateway():
            self.env['amarna.subscription'].cron_expiry_sms()
        self.assertEqual(len(self._new_sms), 1)

    def test_no_phone_number_means_a_note_and_no_sms(self):
        self.env.company.amarna_sms_expiry_enabled = True
        nobody = self.env['res.partner'].create({'name': 'Sans numéro'})
        sub = self._ending_in(2, nobody)
        with self.mockSMSGateway():
            self.env['amarna.subscription'].cron_expiry_sms()
        self.assertFalse(self._new_sms)
        self.assertIn('pas de numéro', ''.join(sub.message_ids.mapped('body')))

    def test_a_typo_in_the_text_does_not_break_the_send(self):
        self.env.company.amarna_sms_expiry_enabled = True
        self.env.company.amarna_sms_expiry_body = 'Bonjour {nom}, fin le {date}'
        sub = self._ending_in(2)
        with self.mockSMSGateway():
            self.assertTrue(sub._send_expiry_sms())
        self.assertEqual(self._new_sms.body, 'Bonjour {nom}, fin le {date}')
