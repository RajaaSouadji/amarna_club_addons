# -*- coding: utf-8 -*-
"""Move billing VAT from the auto-created products onto the records.

Before 17.0.3.1.0 the tax of a reservation or a plan came from its product.
The tax is now stored on the activity and the plan (admin-editable). Copy the
tax that was in use, so amounts do not change when the module is upgraded.
"""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Company default: the sale tax Odoo already applies to new products.
    for company in env['res.company'].with_context(active_test=False).search([]):
        if not company.amarna_default_tax_id and company.account_sale_tax_id:
            company.amarna_default_tax_id = company.account_sale_tax_id

    Product = env['product.product'].with_context(active_test=False)

    for activity in env['amarna.club.activity'].with_context(active_test=False).search([]):
        if activity.tax_ids:
            continue
        product = Product.search([('default_code', '=', 'AMARNA-ACT-%s' % activity.code)], limit=1)
        if product and product.taxes_id:
            activity.tax_ids = product.taxes_id

    for plan in env['amarna.subscription.plan'].with_context(active_test=False).search([]):
        if plan.tax_ids:
            continue
        product = plan.product_id or Product.search(
            [('default_code', '=', 'AMARNA-PLAN-%s' % plan.id)], limit=1)
        if product and product.taxes_id:
            plan.tax_ids = product.taxes_id
