# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install', 'amarna')
class TestInventory(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Item = cls.env['amarna.club.inventory.item']

    def _item(self, **vals):
        vals.setdefault('name', 'Chlore test')
        return self.Item.create(vals)

    def test_low_stock_flag_follows_quantity(self):
        item = self._item(qty=10, low_threshold=4)
        self.assertFalse(item.is_low)
        item.qty = 4
        self.assertTrue(item.is_low, 'Le seuil lui-même compte comme stock bas')
        item.qty = 12
        self.assertFalse(item.is_low)

    def test_negative_values_are_refused(self):
        with self.assertRaises(ValidationError):
            self._item(qty=-1)
        with self.assertRaises(ValidationError):
            self._item(qty=1, low_threshold=-1)

    def test_activity_follows_the_mobile_code(self):
        pool = self.env['amarna.club.activity'].search([('code', '=', 'pool')], limit=1)
        item = self._item(mobile_activity_code='pool')
        self.assertEqual(item.activity_id, pool)


@tagged('post_install', '-at_install', 'amarna')
class TestStockLedger(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Item = cls.env['amarna.club.inventory.item']
        cls.Move = cls.env['amarna.club.inventory.move']
        cls.item = cls.Item.create({
            'name': 'Chlore registre', 'code': 'inv-test-ledger',
            'qty': 10, 'low_threshold': 3, 'reorder_qty': 25})

    def test_entries_and_exits_move_the_quantity(self):
        self.Move.create({'item_id': self.item.id, 'move_type': 'in', 'qty': 5})
        self.assertEqual(self.item.qty, 15)
        self.Move.create({'item_id': self.item.id, 'move_type': 'out',
                          'reason': 'consumption', 'qty': 4})
        self.assertEqual(self.item.qty, 11)

    def test_cannot_take_out_more_than_in_stock(self):
        with self.assertRaises(ValidationError):
            self.Move.create({'item_id': self.item.id, 'move_type': 'out', 'qty': 99})

    def test_tablet_quantity_write_is_journaled_as_adjustment(self):
        before = self.Move.search_count([('item_id', '=', self.item.id)])
        self.item.write({'qty': 7})
        moves = self.Move.search([('item_id', '=', self.item.id)])
        self.assertEqual(len(moves), before + 1)
        self.assertEqual(moves[0].move_type, 'adjust')
        self.assertEqual(moves[0].qty_delta, -3)
        self.assertEqual(self.item.qty, 7)
        # Writing the same quantity again leaves no line.
        self.item.write({'qty': 7})
        self.assertEqual(self.Move.search_count([('item_id', '=', self.item.id)]), before + 1)

    def test_moves_cannot_be_edited_or_deleted(self):
        move = self.Move.create({'item_id': self.item.id, 'move_type': 'in', 'qty': 1})
        with self.assertRaises(UserError):
            move.qty = 50
        user = self.env['res.users'].create({
            'name': 'Magasinier', 'login': 'magasinier.test',
            'group_ids': [(6, 0, [self.env.ref('abonnement_amarna.group_club_user').id])]})
        with self.assertRaises(UserError):
            move.with_user(user).unlink()

    def test_reorder_suggestion(self):
        self.assertEqual(self.item.to_order_qty, 0)
        self.item.write({'qty': 2})
        self.assertEqual(self.item.to_order_qty, 25)
        self.item.reorder_qty = 0
        self.assertEqual(self.item.to_order_qty, 2)   # threshold - qty + 1

    def test_physical_count_adjusts_the_differences_only(self):
        other = self.Item.create({'name': 'Balles test', 'code': 'inv-test-count',
                                  'qty': 20, 'low_threshold': 2})
        location = self.env['amarna.club.inventory.location'].create({'name': 'Armoire test'})
        (self.item | other).location_id = location
        count = self.env['amarna.club.inventory.count'].create({'location_id': location.id})
        self.assertNotEqual(count.name, 'Nouveau')
        count.action_load_items()
        self.assertEqual(len(count.line_ids), 2)
        line = count.line_ids.filtered(lambda l: l.item_id == self.item)
        line.counted_qty = 8
        self.assertEqual(line.difference, -2)
        count.action_validate()
        self.assertEqual(count.state, 'done')
        self.assertEqual(self.item.qty, 8)
        self.assertEqual(other.qty, 20)
        move = self.Move.search([('item_id', '=', self.item.id), ('reason', '=', 'count')])
        self.assertEqual(move.qty_delta, -2)
