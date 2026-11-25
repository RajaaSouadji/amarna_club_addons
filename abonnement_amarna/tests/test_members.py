# -*- coding: utf-8 -*-
"""Member card, suspension, cancellation reason and renewal reminder."""
from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install', 'amarna')
class TestMembers(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.context_today(cls.env.user)
        cls.partner = cls.env['res.partner'].create({'name': 'Membre suspendu', 'email': 'm@example.com'})
        cls.activity = cls.env['amarna.club.activity'].search([('code', '=', 'gym')], limit=1)
        cls.activity.write({'mobile_status': 'open'})
        sub_type = cls.env['amarna.subscription.type'].create({
            'name': 'Mensuel membres', 'duration_value': 1, 'duration_unit': 'month'})
        cls.plan = cls.env['amarna.subscription.plan'].create({
            'name': 'Forfait membres', 'activity_id': cls.activity.id,
            'subscription_type_id': sub_type.id, 'list_price': 0.0})
        cls.card = cls.env['amarna.rfid.card'].create({'partner_id': cls.partner.id})
        cls.card.write({'state': 'active'})
        cls.sub = cls.env['amarna.subscription'].create({
            'partner_id': cls.partner.id, 'plan_id': cls.plan.id,
            'rfid_card_id': cls.card.id, 'start_date': cls.today})
        cls.sub.action_confirm()

    def _freeze(self, start, end):
        self.env['amarna.subscription.freeze'].create({
            'subscription_id': self.sub.id, 'date_from': start, 'date_to': end}).action_freeze()

    def test_free_subscription_is_active_and_has_access(self):
        self.assertEqual(self.sub.subscription_status, 'active')
        self.assertTrue(self.env['amarna.rfid.access'].search([('subscription_id', '=', self.sub.id)]))

    def test_freeze_pushes_the_end_date_and_cuts_access(self):
        end_before = self.sub.expiration_date
        self._freeze(self.today, self.today + timedelta(days=9))
        self.assertEqual(self.sub.expiration_date, end_before + timedelta(days=10))
        self.assertTrue(self.sub.is_frozen)
        self.assertEqual(self.sub.subscription_status, 'frozen')
        self.assertIn(self.sub, self.env['amarna.subscription'].search(
            [('subscription_status', '=', 'frozen')]))
        self.assertNotIn(self.sub, self.env['amarna.subscription'].search(
            [('subscription_status', '=', 'active')]))
        access = self.env['amarna.rfid.access'].search(
            [('subscription_id', '=', self.sub.id), ('active', '=', True)])
        self.assertFalse(access, "Aucun accès pendant la suspension")

    def test_future_freeze_keeps_access_until_it_starts(self):
        self._freeze(self.today + timedelta(days=5), self.today + timedelta(days=12))
        self.assertFalse(self.sub.is_frozen)
        self.assertEqual(self.sub.subscription_status, 'active')

    def test_unfreeze_returns_the_unused_days(self):
        end_before = self.sub.expiration_date
        self._freeze(self.today, self.today + timedelta(days=9))
        self.sub.action_unfreeze()
        self.assertFalse(self.sub.is_frozen)
        self.assertEqual(self.sub.subscription_status, 'active')
        self.assertEqual(self.sub.expiration_date, end_before)

    def test_cannot_overlap_two_suspensions(self):
        self._freeze(self.today, self.today + timedelta(days=3))
        with self.assertRaises(UserError):
            self._freeze(self.today + timedelta(days=1), self.today + timedelta(days=5))

    def test_scan_is_refused_while_frozen(self):
        self._freeze(self.today, self.today + timedelta(days=3))
        wizard = self.env['amarna.scan.wizard'].create({'card_id': self.card.id})
        wizard.action_scan()
        self.assertEqual(wizard.result_state, 'denied')
        self.assertIn('suspendu', wizard.result_message)

    def test_minor_flag_follows_the_birth_date(self):
        child = self.env['res.partner'].create({
            'name': 'Enfant', 'amarna_birth_date': self.today.replace(year=self.today.year - 10)})
        adult = self.env['res.partner'].create({
            'name': 'Adulte', 'amarna_birth_date': self.today.replace(year=self.today.year - 30)})
        self.assertTrue(child.amarna_is_minor)
        self.assertFalse(adult.amarna_is_minor)

    def test_member_action_lists_partners_with_a_subscription(self):
        members = self.env['res.partner'].search(
            self.env.ref('abonnement_amarna.action_amarna_members').domain and
            [('amarna_subscription_ids', '!=', False)])
        self.assertIn(self.partner, members)
        self.assertEqual(self.partner.amarna_subscription_count, 1)

    def test_reminder_needs_an_email_and_posts_a_note(self):
        self.sub.action_send_reminder()
        self.assertTrue(self.env['mail.mail'].search([('recipient_ids', 'in', self.partner.ids)]))
        self.partner.email = False
        with self.assertRaises(UserError):
            self.sub.action_send_reminder()

    def test_cancelling_keeps_the_reason(self):
        reason = self.env.ref('abonnement_amarna.close_reason_moved')
        self.sub.action_cancel()
        self.sub.close_reason_id = reason
        self.assertEqual(self.sub.subscription_status, 'cancelled')
        self.assertEqual(self.sub.close_reason_id.name, 'Déménagement')

    def test_member_created_from_the_menu_is_listed_and_form_is_short(self):
        action = self.env.ref('abonnement_amarna.action_amarna_members')
        context = {'default_amarna_is_member': True}
        new_member = self.env['res.partner'].with_context(**context).create({'name': 'Nouveau membre'})
        self.assertTrue(new_member.amarna_is_member)
        listed = self.env['res.partner'].search(eval(action.domain))
        self.assertIn(new_member, listed)
        self.assertIn(self.partner, listed)
        # the dedicated form has none of the standard contact tabs
        form = self.env.ref('abonnement_amarna.view_amarna_member_form')
        arch = self.env['res.partner'].get_view(form.id, 'form')['arch']
        for tab in ('sales_purchases', 'accounting', 'contact_addresses', 'internal_notes'):
            self.assertNotIn(tab, arch)
        self.assertIn('amarna_medical_certificate_end', arch)
