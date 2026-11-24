# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install', 'amarna')
class TestStaffCertifications(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.context_today(cls.env.user)
        cls.pool = cls.env['amarna.club.activity'].search([('code', '=', 'pool')], limit=1)
        cls.cert_type = cls.env['amarna.club.certification.type'].create({
            'name': 'Brevet MNS test', 'validity_months': 12, 'role': 'lifeguard',
            'activity_ids': [(6, 0, cls.pool.ids)]})
        cls.guard = cls.env['amarna.club.staff'].create({'name': 'Garde test', 'role': 'lifeguard'})

    def _certify(self, obtained):
        return self.env['amarna.club.certification'].create({
            'staff_id': self.guard.id, 'type_id': self.cert_type.id, 'date_obtained': obtained})

    def test_expiry_follows_the_type_validity(self):
        cert = self._certify(self.today)
        self.assertEqual(cert.date_end, self.today + (self.today.replace(year=self.today.year + 1) - self.today))
        self.assertEqual(cert.state, 'valid')

    def test_states(self):
        self.assertEqual(self._certify(self.today - timedelta(days=400)).state, 'expired')
        self.assertEqual(self._certify(self.today - timedelta(days=330)).state, 'expiring')
        forever = self.env['amarna.club.certification.type'].create({'name': 'Permis à vie'})
        cert = self.env['amarna.club.certification'].create({
            'staff_id': self.guard.id, 'type_id': forever.id})
        self.assertFalse(cert.date_end)
        self.assertEqual(cert.state, 'permanent')

    def test_assignment_is_free_until_the_club_enforces_certifications(self):
        self.guard.activity_ids = self.pool       # no certificate, rule off: fine

    def test_enforced_rule_blocks_assignment_without_valid_certificate(self):
        self.env.company.amarna_staff_enforce_certifications = True
        with self.assertRaises(ValidationError):
            self.guard.activity_ids = self.pool
        self._certify(self.today - timedelta(days=400))    # expired: still refused
        with self.assertRaises(ValidationError):
            self.guard.activity_ids = self.pool
        self._certify(self.today)
        self.guard.activity_ids = self.pool
        self.assertEqual(self.guard.activity_ids, self.pool)

    def test_rule_only_concerns_the_matching_role_and_activity(self):
        self.env.company.amarna_staff_enforce_certifications = True
        technician = self.env['amarna.club.staff'].create({'name': 'Tech test', 'role': 'technician'})
        technician.activity_ids = self.pool            # the diploma targets lifeguards
        gym = self.env['amarna.club.activity'].search([('code', '=', 'gym')], limit=1)
        self.guard.activity_ids = gym                  # and the pool only

    def test_staff_card_counts_certification_alerts(self):
        self._certify(self.today - timedelta(days=400))
        self._certify(self.today - timedelta(days=330))
        self.assertEqual(self.guard.expired_certification_count, 1)
        self.assertEqual(self.guard.expiring_certification_count, 1)


@tagged('post_install', '-at_install', 'amarna')
class TestShifts(TransactionCase):

    def test_a_person_cannot_have_two_overlapping_shifts(self):
        pool = self.env['amarna.club.activity'].search([('code', '=', 'pool')], limit=1)
        staff = self.env['amarna.club.staff'].create({'name': 'Garde planning', 'role': 'lifeguard'})
        start = fields.Datetime.now() + timedelta(days=1)
        Shift = self.env['amarna.club.shift']
        shift = Shift.create({
            'staff_id': staff.id, 'activity_id': pool.id,
            'start_at': start, 'end_at': start + timedelta(hours=4)})
        self.assertEqual(shift.duration, 4.0)
        with self.assertRaises(ValidationError):
            Shift.create({'staff_id': staff.id, 'activity_id': pool.id,
                          'start_at': start + timedelta(hours=3), 'end_at': start + timedelta(hours=6)})
        Shift.create({'staff_id': staff.id, 'activity_id': pool.id,
                      'start_at': start + timedelta(hours=4), 'end_at': start + timedelta(hours=8)})
        with self.assertRaises(ValidationError):
            Shift.create({'staff_id': staff.id, 'activity_id': pool.id,
                          'start_at': start, 'end_at': start - timedelta(hours=1)})
