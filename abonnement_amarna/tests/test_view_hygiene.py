# -*- coding: utf-8 -*-
"""Guards against visual bugs that no server-side test would otherwise notice.

* Odoo 17-style chatter (``<div class="oe_chatter">`` with the mail fields in
  it) is no longer interpreted by Odoo 20: the raw follower / message tables
  were drawn beside the sheet and squeezed the form into a few pixels.
* A model without a ``name`` shows up as ``model,id`` in the breadcrumb and
  the form header unless it computes its own display name.
"""
from odoo.models import BaseModel
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

MAIL_FIELDS = ('message_ids', 'message_follower_ids', 'message_partner_ids')


@tagged('post_install', '-at_install', 'amarna')
class TestViewHygiene(TransactionCase):

    def test_no_legacy_chatter_in_views(self):
        views = self.env['ir.ui.view'].search([('model', 'like', 'amarna.')])
        self.assertTrue(views, "Aucune vue Amarna trouvée")
        for view in views:
            arch = view.arch_db or ''
            self.assertNotIn('oe_chatter', arch, "%s : utiliser <chatter/>" % view.xml_id)
            for name in MAIL_FIELDS:
                self.assertNotIn(
                    'name="%s"' % name, arch,
                    "%s : champ technique %s affiché tel quel, utiliser <chatter/>" % (view.xml_id, name))

    def test_every_model_has_a_readable_name(self):
        nameless = []
        for model_name, Model in self.env.registry.items():
            if not model_name.startswith('amarna.') or Model._transient or Model._abstract:
                continue
            has_name = Model._rec_name in Model._fields
            overridden = Model._compute_display_name is not BaseModel._compute_display_name
            if not (has_name or overridden):
                nameless.append(model_name)
        self.assertFalse(
            nameless,
            "Sans champ nom ni _compute_display_name (affichés « modèle,id » dans le fil d'Ariane) : %s"
            % ', '.join(sorted(nameless)))
