# -*- coding: utf-8 -*-
"""Money path: subscribe -> invoice -> pay -> access -> renew -> pay again,
and reservations paid at the desk or covered by a subscription.

Run on a scratch database only:
    odoo -d <scratch> -u abonnement_amarna --test-enable --test-tags amarna --stop-after-init
"""
from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form, tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install', 'amarna')
class TestAmarnaBilling(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env['res.partner'].create({'name': 'Membre test'})
        cls.activity = cls.env['amarna.club.activity'].search([('code', '=', 'gym')], limit=1)
        cls.activity.write({'unit_price': 20.0, 'mobile_status': 'open'})
        cls.sub_type = cls.env['amarna.subscription.type'].create({
            'name': 'Mensuel test', 'duration_value': 1, 'duration_unit': 'month',
        })
        cls.plan = cls.env['amarna.subscription.plan'].create({
            'name': 'Forfait 10 séances test',
            'activity_id': cls.activity.id,
            'subscription_type_id': cls.sub_type.id,
            'list_price': 100.0,
            'session_count': 10,
        })
        cls.card = cls.env['amarna.rfid.card'].create({'partner_id': cls.partner.id})
        cls.card.write({'state': 'active'})

    # ------------------------------------------------------------ helpers

    def _pay_open_invoices(self, record, amount=None):
        """Register a payment through the standard Odoo wizard."""
        invoices = record.invoice_ids.filtered(
            lambda m: m.state == 'posted' and m.amount_residual > 0)
        self.assertTrue(invoices, 'Aucune facture ouverte à encaisser')
        wizard_vals = {}
        if amount is not None:
            wizard_vals['amount'] = amount
        wizard = self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=invoices.ids,
        ).create(wizard_vals)
        wizard.action_create_payments()

    def _new_subscription(self, **extra):
        vals = {'partner_id': self.partner.id, 'plan_id': self.plan.id,
                'rfid_card_id': self.card.id, 'start_date': fields.Date.context_today(self.env.user)}
        vals.update(extra)
        return self.env['amarna.subscription'].create(vals)

    # -------------------------------------------------------- subscriptions

    def test_subscription_defaults_and_lines(self):
        sub = self._new_subscription()
        self.assertEqual(sub.state, 'draft')
        self.assertEqual(sub.remaining_sessions, 10)
        self.assertAlmostEqual(sub.amount_untaxed, 100.0)
        self.assertEqual(len(sub.line_ids), 1)
        self.assertFalse(sub.payment_valid, 'Un abonnement non payé ne doit pas être valide')
        self.assertEqual(sub.billing_state, 'to_invoice')

    def test_expiration_uses_calendar_months(self):
        sub = self._new_subscription(start_date=fields.Date.to_date('2026-01-15'))
        self.assertEqual(sub.expiration_date, fields.Date.to_date('2026-02-14'))

    def test_full_money_path(self):
        sub = self._new_subscription()
        sub.action_confirm()
        self.assertEqual(sub.state, 'confirmed')
        self.assertEqual(sub.subscription_status, 'unpaid')
        self.assertFalse(self.env['amarna.rfid.access'].search_count(
            [('subscription_id', '=', sub.id), ('state', '!=', 'cancelled')]),
            'Accès accordé avant paiement')

        sub.action_create_invoice()
        invoice = sub.invoice_ids
        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.state, 'posted')
        self.assertEqual(sub.billing_state, 'unpaid')
        self.assertAlmostEqual(sub.amount_due, invoice.amount_total)

        self._pay_open_invoices(sub)
        self.assertEqual(sub.billing_state, 'paid')
        self.assertTrue(sub.payment_valid)
        self.assertEqual(sub.subscription_status, 'active')
        self.assertTrue(self.env['amarna.rfid.access'].search_count(
            [('subscription_id', '=', sub.id), ('state', '!=', 'cancelled')]),
            'Accès non accordé après paiement')

    def test_partial_payment(self):
        sub = self._new_subscription()
        sub.action_confirm()
        sub.action_create_invoice()
        total = sub.amount_total
        self._pay_open_invoices(sub, amount=total / 2)
        self.assertEqual(sub.billing_state, 'partial')
        self.assertFalse(sub.payment_valid)
        self._pay_open_invoices(sub)
        self.assertEqual(sub.billing_state, 'paid')

    def test_renewal_requires_new_payment(self):
        sub = self._new_subscription()
        sub.action_confirm()
        sub.action_create_invoice()
        self._pay_open_invoices(sub)
        old_end = sub.expiration_date

        sub.action_renew()
        self.assertEqual(sub.start_date, old_end + timedelta(days=1))
        self.assertEqual(sub.remaining_sessions, 10)
        self.assertEqual(len(sub.invoice_ids), 2, 'Le renouvellement doit émettre une facture')
        self.assertEqual(sub.billing_state, 'unpaid')
        self.assertFalse(sub.payment_valid, 'La nouvelle période ne doit pas être gratuite')
        self.assertFalse(self.env['amarna.rfid.access'].search_count(
            [('subscription_id', '=', sub.id), ('state', '!=', 'cancelled')]))

        self._pay_open_invoices(sub)
        self.assertTrue(sub.payment_valid)

    def test_cannot_invoice_twice_for_same_period(self):
        sub = self._new_subscription()
        sub.action_confirm()
        sub.action_create_invoice()
        with self.assertRaises(UserError):
            sub.action_create_invoice()

    def test_free_plan_needs_no_invoice(self):
        free_plan = self.plan.copy({'name': 'Gratuit test', 'list_price': 0.0})
        sub = self._new_subscription(plan_id=free_plan.id)
        sub.action_confirm()
        self.assertEqual(sub.billing_state, 'free')
        self.assertTrue(sub.payment_valid)
        with self.assertRaises(UserError):
            sub.action_create_invoice()

    def test_one_subscription_per_activity(self):
        self._new_subscription().action_confirm()
        second = self._new_subscription()
        with self.assertRaises(ValidationError):
            second.action_confirm()

    def test_scan_wizard_denies_unpaid_subscription(self):
        sub = self._new_subscription()
        sub.action_confirm()
        wizard = self.env['amarna.scan.wizard'].create({'card_id': self.card.id})
        wizard.action_scan()
        self.assertEqual(wizard.result_state, 'denied')
        self.assertIn('Paiement en attente', wizard.result_message)

    # --------------------------------------------------------- reservations

    def _new_reservation(self, **extra):
        day = fields.Date.context_today(self.env.user) + timedelta(days=2)
        vals = {
            'activity_id': self.activity.id,
            'mobile_activity_code': self.activity.code,
            'partner_id': self.partner.id,
            'client_name': 'Membre test',
            'reservation_date': day,
            'start_hour': 10.0,
            'end_hour': 11.0,
            'people_count': 2,
        }
        vals.update(extra)
        return self.env['amarna.club.reservation'].create(vals)

    def test_reservation_priced_per_person(self):
        resa = self._new_reservation()
        self.assertAlmostEqual(resa.amount_untaxed, 40.0)
        self.assertEqual(resa.billing_state, 'to_invoice')
        self.assertFalse(resa.payment_valid)

    def test_reservation_check_in_blocked_until_paid(self):
        resa = self._new_reservation()
        resa.action_confirm()
        with self.assertRaises(ValidationError):
            resa.action_check_in()
        self.assertNotEqual(resa.status, 'checkedin')

        resa.action_create_invoice()
        self._pay_open_invoices(resa)
        self.assertTrue(resa.payment_valid)
        resa.action_check_in()
        self.assertEqual(resa.status, 'checkedin')

    def test_reservation_covered_by_subscription_uses_sessions(self):
        sub = self._new_subscription()
        sub.action_confirm()
        sub.action_create_invoice()
        self._pay_open_invoices(sub)

        resa = self._new_reservation(subscription_id=sub.id)
        self.assertEqual(resa.amount_untaxed, 0.0)
        self.assertEqual(resa.billing_state, 'free')
        resa.action_confirm()
        resa.action_check_in()
        self.assertEqual(sub.remaining_sessions, 8, 'Deux personnes doivent décompter deux séances')

    def test_cancelled_reservation_revokes_access(self):
        resa = self._new_reservation(rfid_card_id=self.card.id)
        resa.action_create_invoice()
        self._pay_open_invoices(resa)
        self.assertTrue(self.env['amarna.rfid.access'].search_count(
            [('reservation_id', '=', resa.id), ('state', '!=', 'cancelled')]))
        resa.action_cancel()
        self.assertFalse(self.env['amarna.rfid.access'].search_count(
            [('reservation_id', '=', resa.id), ('state', '!=', 'cancelled')]))

    def test_invoice_carries_origin_links(self):
        resa = self._new_reservation()
        resa.action_create_invoice()
        invoice = resa.invoice_ids
        self.assertEqual(invoice.amarna_reservation_id, resa)
        self.assertEqual(invoice.amarna_period_start, resa.reservation_date)
        self.assertTrue(invoice.invoice_line_ids.product_id.default_code.startswith('AMARNA-ACT-'))

    # ------------------------------------------------- Findings of the field test

    def test_cancelled_unbilled_reservation_owes_nothing(self):
        resa = self._new_reservation()
        self.assertEqual(resa.billing_state, 'to_invoice')
        resa.action_cancel()
        self.assertEqual(resa.billing_state, 'free')
        self.assertEqual(resa.amount_total, 0.0)

    def test_invoice_label_does_not_repeat_the_activity_name(self):
        # The tablet names bookings "Activité – Client".
        resa = self._new_reservation(name='%s – Membre test' % self.activity.name)
        resa.action_confirm()
        resa.action_create_invoice()
        line = resa.invoice_ids.invoice_line_ids
        self.assertEqual(line.name, resa.name)

    def test_invoice_knows_the_activity_it_bills(self):
        sub = self._new_subscription()
        sub.action_confirm()
        sub.action_create_invoice()
        self.assertEqual(sub.invoice_ids.amarna_activity_id, self.activity)
        resa = self._new_reservation()
        resa.action_confirm()
        resa.action_create_invoice()
        self.assertEqual(resa.invoice_ids.amarna_activity_id, self.activity)

    def test_front_desk_role_can_bill_and_collect(self):
        group = self.env.ref('abonnement_amarna.group_club_user')
        user = self.env['res.users'].create({
            'name': 'Accueil test', 'login': 'accueil_test_amarna',
            'groups_id': [(6, 0, [group.id])],
        })
        self.assertTrue(user.has_group('account.group_account_invoice'))

    def test_check_in_refusal_shows_a_formatted_amount(self):
        resa = self._new_reservation()
        resa.action_confirm()
        with self.assertRaises(ValidationError) as raised:
            resa.action_check_in()
        self.assertIn(self.company.currency_id.symbol, str(raised.exception))
