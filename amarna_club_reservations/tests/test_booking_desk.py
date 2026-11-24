# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install', 'amarna')
class TestBookingDesk(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.padel = cls.env['amarna.club.activity'].search([('code', '=', 'padel')], limit=1)
        cls.padel.mobile_status = 'open'
        cls.court = cls.env['amarna.club.resource'].create({
            'name': 'Terrain test', 'activity_id': cls.padel.id})
        cls.day = fields.Date.context_today(cls.env.user) + timedelta(days=10)
        cls.Reservation = cls.env['amarna.club.reservation']
        cls.member = cls.env['res.partner'].create({'name': 'Joueur test'})

    def _book(self, start=18.0, end=19.0, **vals):
        return self.Reservation.create(dict({
            'activity_id': self.padel.id, 'resource_id': self.court.id,
            'partner_id': self.member.id, 'reservation_date': self.day,
            'start_hour': start, 'end_hour': end, 'people_count': 1}, **vals))

    def test_a_court_cannot_be_booked_twice_on_the_same_slot(self):
        self._book(18.0, 19.0)
        with self.assertRaises(ValidationError):
            self._book(18.5, 19.5)
        self._book(19.0, 20.0)      # back to back is fine

    def test_a_whole_court_accepts_a_group_of_four(self):
        self._book(18.0, 19.0, people_count=4)

    def test_cancelled_booking_frees_the_court(self):
        first = self._book(18.0, 19.0)
        first.action_cancel()
        self._book(18.0, 19.0)

    def test_resource_capacity_counts_people(self):
        group = self.env['amarna.club.resource'].create({
            'name': 'Couloir test', 'activity_id': self.padel.id, 'capacity': 4})
        self._book(resource_id=group.id, people_count=3)
        self._book(resource_id=group.id, people_count=1)
        with self.assertRaises(ValidationError):
            self._book(resource_id=group.id, people_count=1)

    def test_booking_without_resource_still_works_for_the_tablet(self):
        self._book(resource_id=False)
        self._book(resource_id=False)

    def test_waiting_list_promotes_the_first_entry_on_cancellation(self):
        booked = self._book(18.0, 19.0)
        waiting = self.env['amarna.club.reservation.waiting'].create({
            'partner_id': self.env['res.partner'].create({'name': 'En attente test'}).id,
            'activity_id': self.padel.id, 'resource_id': self.court.id,
            'reservation_date': self.day, 'start_hour': 18.0, 'end_hour': 19.0})
        later = self.env['amarna.club.reservation.waiting'].create({
            'partner_id': self.member.id, 'activity_id': self.padel.id,
            'resource_id': self.court.id, 'reservation_date': self.day,
            'start_hour': 18.0, 'end_hour': 19.0})
        with self.assertRaises(ValidationError):
            waiting.action_promote()     # still full
        booked.action_cancel()
        self.assertEqual(waiting.state, 'promoted')
        self.assertTrue(waiting.reservation_id)
        self.assertEqual(later.state, 'waiting')    # only one place was freed

    def test_repeat_weekly_skips_conflicts_and_reports_them(self):
        source = self._book(18.0, 19.0)
        # Someone already holds the court on the 2nd following week.
        self._book(18.0, 19.0, reservation_date=self.day + timedelta(weeks=2),
                   partner_id=self.env['res.partner'].create({'name': 'Autre'}).id)
        wizard = self.env['amarna.club.reservation.repeat'].create({
            'reservation_id': source.id, 'weeks': 3})
        wizard.action_repeat()
        copies = self.Reservation.search([
            ('resource_id', '=', self.court.id), ('partner_id', '=', self.member.id)])
        self.assertEqual(len(copies), 3)        # source + week 1 + week 3
        self.assertIn('Non créées', wizard.result)
        self.assertIn('2 réservation(s) créée(s)', wizard.result)

    def test_late_cancellation_and_no_show_flags(self):
        self.env.company.amarna_reservation_late_cancel_hours = 48
        soon = self.Reservation.create({
            'activity_id': self.padel.id, 'partner_id': self.member.id,
            'start_at': fields.Datetime.now() + timedelta(hours=5),
            'end_at': fields.Datetime.now() + timedelta(hours=6), 'people_count': 1})
        soon.action_cancel()
        self.assertTrue(soon.late_cancel)
        far = self._book(10.0, 11.0)       # 10 days away
        far.action_cancel()
        self.assertFalse(far.late_cancel)
        absent = self._book(12.0, 13.0)
        absent.action_no_show()
        self.assertTrue(absent.no_show)
        self.assertEqual(absent.status, 'cancelled')
