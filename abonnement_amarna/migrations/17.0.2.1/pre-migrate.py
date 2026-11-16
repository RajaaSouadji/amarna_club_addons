# -*- coding: utf-8 -*-
"""Close the open access rules left by earlier releases.

Earlier versions shipped ``ir.model.access`` rows without a group on every
Amarna model, which grants access to public and portal users too. Odoo never
deletes access rows that disappear from a CSV, so they are removed here and
the restricted rows of the current CSV are created by the normal load.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute(
        """
        DELETE FROM ir_model_access acc
         USING ir_model m
         WHERE acc.model_id = m.id
           AND acc.group_id IS NULL
           AND m.model LIKE %s
        """,
        ('amarna.%',),
    )
    _logger.info('abonnement_amarna: removed %s open access rules', cr.rowcount)

    # Drop the XML ids that pointed at the rows deleted above, so the CSV
    # load recreates them with their new group.
    cr.execute(
        """
        DELETE FROM ir_model_data d
         WHERE d.module = 'abonnement_amarna'
           AND d.model = 'ir.model.access'
           AND NOT EXISTS (
                SELECT 1 FROM ir_model_access a WHERE a.id = d.res_id)
        """
    )
