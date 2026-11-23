# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
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

    def test_home_screen_counts_low_stock_per_activity(self):
        pool = self.env['amarna.club.activity'].search([('code', '=', 'pool')], limit=1)
        before = pool.low_stock_count
        item = self._item(mobile_activity_code='pool', qty=1, low_threshold=3)
        pool.invalidate_recordset(['low_stock_count'])
        self.assertEqual(pool.low_stock_count, before + 1)
        item.qty = 10
        pool.invalidate_recordset(['low_stock_count'])
        self.assertEqual(pool.low_stock_count, before)
