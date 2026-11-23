# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install', 'amarna')
class TestInterventions(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Ticket = cls.env['amarna.club.intervention']
        cls.pool = cls.env['amarna.club.activity'].search([('code', '=', 'pool')], limit=1)

    def test_activity_follows_the_mobile_code(self):
        ticket = self.Ticket.create({'name': 'Fuite', 'mobile_activity_code': 'pool'})
        self.assertEqual(ticket.activity_id, self.pool)

    def test_asset_and_technician_are_resolved_from_the_tablet_payload(self):
        asset = self.env['amarna.club.asset'].create(
            {'name': 'Pompe', 'code': 'asset-test-pump', 'mobile_activity_code': 'pool'})
        user = self.env['res.users'].create(
            {'name': 'Mourad Haddad Test', 'login': 'mourad.test'})
        staff = self.env['amarna.club.staff'].create(
            {'name': 'Mourad Haddad Test', 'role': 'technician', 'user_id': user.id})
        ticket = self.Ticket.create({
            'name': 'Pompe HS', 'mobile_asset_code': 'asset-test-pump',
            'assigned_to': 'Mourad Haddad Test'})
        self.assertEqual(ticket.asset_id, asset)
        self.assertEqual(ticket.staff_id, staff)
        self.assertEqual(ticket.user_id, user)

    def test_technician_chosen_in_odoo_is_what_the_tablet_reads(self):
        staff = self.env['amarna.club.staff'].create(
            {'name': 'Yacine Test', 'role': 'technician'})
        ticket = self.Ticket.create({'name': 'Choisi dans Odoo', 'staff_id': staff.id})
        self.assertEqual(ticket.assigned_to, 'Yacine Test')
        self.assertFalse(ticket.user_id)

    def test_unknown_technician_name_is_kept_as_text(self):
        ticket = self.Ticket.create({'name': 'Externe', 'assigned_to': 'Prestataire X'})
        self.assertEqual(ticket.assigned_to, 'Prestataire X')
        self.assertFalse(ticket.staff_id)

    def test_legacy_description_still_gives_id_and_type(self):
        ticket = self.Ticket.create({
            'name': 'Ancien format',
            'description': 'Type: preventive\n[Mobile ID: t-42]'})
        self.assertEqual(ticket.mobile_id, 't-42')
        self.assertEqual(ticket.type, 'preventive')

    def test_unknown_enum_values_are_rejected_loudly(self):
        for field_name in ('type', 'priority', 'status'):
            with self.assertRaises(ValidationError, msg=field_name):
                self.Ticket.create({'name': 'Mauvais', field_name: 'bogus'})

    def test_resolution_is_stamped_once_and_reopen_clears_it(self):
        ticket = self.Ticket.create({'name': 'À résoudre'})
        ticket.action_take_over()
        self.assertEqual(ticket.status, 'inProgress')
        ticket.action_resolve()
        stamp = ticket.date_completed
        self.assertTrue(stamp)
        ticket.write({'description': 'précision'})
        self.assertEqual(ticket.date_completed, stamp)
        ticket.action_reopen()
        self.assertEqual((ticket.status, ticket.date_completed), ('open', False))

    def test_overdue_only_while_not_resolved(self):
        late = fields.Datetime.now() - timedelta(days=1)
        ticket = self.Ticket.create({'name': 'En retard', 'date_due': late})
        self.assertTrue(ticket.is_overdue)
        ticket.action_resolve()
        self.assertFalse(ticket.is_overdue)

    def test_due_date_default_comes_from_the_club_settings(self):
        self.env.company.amarna_ticket_due_days = 5
        ticket = self.Ticket.create({'name': 'Délai'})
        delta = ticket.date_due - fields.Datetime.now()
        self.assertTrue(timedelta(days=4, hours=23) < delta <= timedelta(days=5))

    def test_kanban_shows_every_status_column(self):
        result = self.Ticket.with_context(read_group_expand=True).web_read_group(
            [], ['status'], ['__count'])
        self.assertEqual(
            {g['status'] for g in result['groups']}, {'open', 'inProgress', 'resolved'})

    def test_home_screen_counts_open_tickets_per_activity(self):
        before = self.pool.open_ticket_count
        ticket = self.Ticket.create({'name': 'Compteur', 'mobile_activity_code': 'pool'})
        self.pool.invalidate_recordset(['open_ticket_count'])
        self.assertEqual(self.pool.open_ticket_count, before + 1)
        ticket.action_resolve()
        self.pool.invalidate_recordset(['open_ticket_count'])
        self.assertEqual(self.pool.open_ticket_count, before)
