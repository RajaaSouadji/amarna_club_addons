# -*- coding: utf-8 -*-
from odoo import api, fields, models

# (code, name, type): how the club is paid. Choosing the journal in the payment window
# is choosing the method; the daily "Paiements du club" list can be grouped by it.
PAYMENT_JOURNALS = (
    ('ESP', 'Espèces (caisse)', 'cash'),
    ('CHQ', 'Chèques', 'bank'),
    ('CIB', 'Carte CIB / TPE', 'bank'),
)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    amarna_club = fields.Boolean(
        string='Paiement du club', copy=False, index=True,
        help="Vrai quand ce paiement règle une facture d'abonnement ou de réservation du club.")
    amarna_activity_id = fields.Many2one(
        'amarna.club.activity', string='Activité', copy=False, index=True,
        help="Activité réglée, pour regrouper les encaissements.")

    def _amarna_tag_from_invoices(self, invoices):
        """Mark these payments as club payments when one of the invoices they settle is a club invoice."""
        club = invoices.filtered(lambda m: m.amarna_subscription_id or m.amarna_reservation_id)
        if not club:
            return
        for payment in self.filtered(lambda p: not p.amarna_club):
            payment.write({'amarna_club': True, 'amarna_activity_id': club[0].amarna_activity_id.id})


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    @api.model
    def _amarna_ensure_payment_journals(self):
        """Cash, cheque and card journals for every company that has a chart of accounts.
        Called at each module update: it only creates what is missing."""
        for company in self.env['res.company'].search([]):
            if not company.chart_template:
                continue
            for code, name, journal_type in PAYMENT_JOURNALS:
                if self.with_company(company).search_count(
                        [('company_id', '=', company.id), ('code', '=', code)]):
                    continue
                self.with_company(company).create({
                    'name': name, 'code': code, 'type': journal_type, 'company_id': company.id})
        return True
