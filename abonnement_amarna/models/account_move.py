# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMove(models.Model):
    """Invoices issued for a subscription or a reservation.

    The invoice is the single source of truth for what is owed and paid. The
    subscription/reservation derives its billing state from these links.
    """
    _inherit = 'account.move'

    amarna_subscription_id = fields.Many2one(
        'amarna.subscription', string='Abonnement Amarna',
        copy=False, index=True, ondelete='set null')
    amarna_reservation_id = fields.Many2one(
        'amarna.club.reservation', string='Réservation Amarna',
        copy=False, index=True, ondelete='set null')
    amarna_period_start = fields.Date(
        string='Début de période Amarna', copy=False, index=True)

    def _amarna_refresh_access(self):
        """Recompute RFID access for every Amarna record these invoices serve."""
        self.mapped('amarna_subscription_id')._sync_rfid_access()
        self.mapped('amarna_reservation_id')._sync_rfid_access()


class AccountPartialReconcile(models.Model):
    """Every payment, reconciliation or un-reconciliation goes through here.

    Hooking the reconciliation (rather than the payment wizard or a button)
    keeps RFID access in step with the books however the money came in:
    the Odoo payment wizard, bank statements, or manual reconciliation.
    """
    _inherit = 'account.partial.reconcile'

    @api.model_create_multi
    def create(self, vals_list):
        partials = super().create(vals_list)
        self.env.flush_all()
        moves = partials.mapped('debit_move_id.move_id') | partials.mapped('credit_move_id.move_id')
        moves._amarna_refresh_access()
        return partials

    def unlink(self):
        moves = self.mapped('debit_move_id.move_id') | self.mapped('credit_move_id.move_id')
        result = super().unlink()
        self.env.flush_all()
        moves._amarna_refresh_access()
        return result
