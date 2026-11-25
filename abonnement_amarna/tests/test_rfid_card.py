# -*- coding: utf-8 -*-
"""One card per member, scanned once: subscriptions and bookings pick it up by themselves."""
from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install', 'amarna')
class TestRfidCard(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.context_today(cls.env.user)
        cls.Card = cls.env['amarna.rfid.card']
        cls.activity = cls.env['amarna.club.activity'].search([('code', '=', 'gym')], limit=1)
        cls.activity.write({'mobile_status': 'open'})
        sub_type = cls.env['amarna.subscription.type'].create({
            'name': 'Mensuel carte', 'duration_value': 1, 'duration_unit': 'month'})
        cls.plan = cls.env['amarna.subscription.plan'].create({
            'name': 'Forfait carte', 'activity_id': cls.activity.id,
            'subscription_type_id': sub_type.id, 'list_price': 0.0})

    def _member(self, name):
        return self.env['res.partner'].create({'name': name})

    def _subscription(self, partner, **extra):
        return self.env['amarna.subscription'].create(dict(
            partner_id=partner.id, plan_id=self.plan.id, start_date=self.today, **extra))

    def test_the_number_read_by_the_reader_is_the_card_name(self):
        card = self.Card.create({'name': '  04A1B2C3  '})
        self.assertEqual(card.name, '04A1B2C3')
        with self.assertRaises(Exception):
            self.Card.create({'name': '04A1B2C3'})     # a number is used once

    def test_a_blank_number_gets_an_internal_one(self):
        first, second = self.Card.create([{'name': '/'}, {'name': ''}])
        self.assertTrue(first.name and first.name != '/')
        self.assertNotEqual(first.name, second.name)

    def test_a_card_given_to_a_member_serves_the_subscriptions_that_had_none(self):
        member = self._member('Membre sans carte')
        sub = self._subscription(member)
        self.assertFalse(sub.rfid_card_id)
        card = self.Card.create({'name': 'CARTE-A', 'partner_id': member.id})
        self.assertEqual(sub.rfid_card_id, card)

    def test_a_new_subscription_takes_the_card_of_the_member(self):
        member = self._member('Membre avec carte')
        card = self.Card.create({'name': 'CARTE-B', 'partner_id': member.id})
        self.assertEqual(self._subscription(member).rfid_card_id, card)
        # an explicit choice of "no card" is kept
        other = self._member('Membre sans badge voulu')
        self.Card.create({'name': 'CARTE-C', 'partner_id': other.id})
        self.assertFalse(self._subscription(other, rfid_card_id=False).rfid_card_id)

    def test_only_one_card_per_member(self):
        member = self._member('Membre deux cartes')
        self.Card.create({'name': 'CARTE-D', 'partner_id': member.id})
        with self.assertRaises(ValidationError):
            self.Card.create({'name': 'CARTE-E', 'partner_id': member.id})

    def test_the_card_shows_who_opens_the_access_and_until_when(self):
        member = self._member('Membre accès')
        card = self.Card.create({'name': 'CARTE-F', 'partner_id': member.id})
        self.assertFalse(card.access_until)
        sub = self._subscription(member)
        sub.action_confirm()
        self.assertTrue(sub.payment_valid, 'a free plan is paid from the start')
        card.invalidate_recordset()
        self.assertEqual(card.state, 'active')
        self.assertTrue(card.access_until)
        self.assertIn(sub.name, card.access_source)
        # lifting a block recomputes the state instead of trusting the button
        card.action_block()
        self.assertEqual(card.state, 'blocked')
        card.action_restore()
        self.assertEqual(card.state, 'active')

    def test_the_card_form_can_start_the_scan_with_its_number(self):
        member = self._member('Membre scan')
        card = self.Card.create({'name': 'CARTE-G', 'partner_id': member.id})
        action = card.action_open_scan()
        self.assertEqual(action['res_model'], 'amarna.scan.wizard')
        wizard = self.env['amarna.scan.wizard'].browse(action['res_id'])
        self.assertEqual(wizard.card_id, card)

    def test_cards_and_access_share_one_menu(self):
        env = self.env
        self.assertTrue(env.ref('abonnement_amarna.menu_amarna_rfid_cards'))
        self.assertFalse(env.ref('abonnement_amarna.menu_amarna_rfid_access', raise_if_not_found=False))
        form = env.ref('abonnement_amarna.view_amarna_rfid_card_form')
        arch = env['amarna.rfid.card'].get_view(form.id, 'form')['arch']
        self.assertIn('access_ids', arch)

    def test_billing_menu_lives_in_invoicing_not_in_subscriptions(self):
        root = self.env.ref('abonnement_amarna.menu_amarna_root')
        self.assertFalse(root.child_id.filtered(lambda m: m.name == 'Facturation'))
        invoices = self.env.ref('abonnement_amarna.menu_amarna_invoices')
        self.assertEqual(invoices.parent_id, self.env.ref('account.menu_finance_receivables'))
