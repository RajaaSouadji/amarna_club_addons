# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install', 'amarna')
class TestMaintenanceParts(TransactionCase):

    def test_parts_leave_the_stock_once_when_the_ticket_is_closed(self):
        item = self.env['amarna.club.inventory.item'].create({
            'name': 'Joint test', 'code': 'inv-test-joint', 'qty': 10, 'low_threshold': 2})
        ticket = self.env['amarna.club.intervention'].create({
            'name': 'Remplacer le joint',
            'part_ids': [(0, 0, {'item_id': item.id, 'qty': 3})]})
        self.assertEqual(item.qty, 10)
        ticket.action_resolve()
        self.assertEqual(item.qty, 7)
        self.assertTrue(ticket.part_ids.consumed)
        # Reopen and close: the parts are not taken a second time.
        ticket.action_reopen()
        ticket.action_resolve()
        self.assertEqual(item.qty, 7)
        move = self.env['amarna.club.inventory.move'].search(
            [('item_id', '=', item.id), ('reason', '=', 'maintenance')])
        self.assertEqual(move.qty_delta, -3)
