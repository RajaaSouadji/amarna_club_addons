from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _sync_amarna_invoice_payment(self):
        Payment = self.env['amarna.subscription.payment']
        for invoice in self.filtered(lambda move: move.move_type == 'out_invoice'):
            subscription = self.env['amarna.subscription'].search(
                [('invoice_id', '=', invoice.id)], limit=1
            )
            if not subscription:
                continue

            generated = Payment.search([
                ('subscription_id', '=', subscription.id),
                ('invoice_id', '=', invoice.id),
                ('source', '=', 'invoice'),
            ])
            reconciled_payments = invoice._get_reconciled_payments()
            synced_ids = []

            # Cas normal : un ou plusieurs paiements sont rapprochés avec la facture.
            for account_payment in reconciled_payments:
                values = {
                    'name': 'Paiement %s' % (account_payment.name or invoice.name),
                    'subscription_id': subscription.id,
                    'payment_date': account_payment.date or invoice.invoice_date or fields.Date.today(),
                    'amount': account_payment.amount,
                    'method': 'other',
                    'state': 'confirmed',
                    'source': 'invoice',
                    'account_payment_id': account_payment.id,
                }
                line = generated.filtered(
                    lambda item: item.account_payment_id == account_payment
                )[:1]
                if line:
                    line.write(values)
                else:
                    line = Payment.create(values)
                synced_ids.append(line.id)

            # Cas d'un crédit non affecté : Odoo affiche déjà un montant payé,
            # mais aucun paiement rapproché n'est encore retourné.
            paid_amount = invoice.amount_total - invoice.amount_residual
            if paid_amount > 0 and not reconciled_payments:
                line = generated.filtered(lambda item: not item.account_payment_id)[:1]
                values = {
                    'name': 'Paiement facture %s' % invoice.name,
                    'subscription_id': subscription.id,
                    'payment_date': invoice.invoice_date or fields.Date.today(),
                    'amount': paid_amount,
                    'method': 'other',
                    'state': 'confirmed',
                    'source': 'invoice',
                }
                if line:
                    line.write(values)
                else:
                    line = Payment.create(values)
                synced_ids.append(line.id)

            generated.filtered(lambda line: line.id not in synced_ids).filtered(
                lambda line: line.state != 'cancelled'
            ).write({'state': 'cancelled'})

    def write(self, vals):
        result = super().write(vals)
        self._sync_amarna_invoice_payment()
        return result


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def action_post(self):
        result = super().action_post()
        self.mapped('reconciled_invoice_ids')._sync_amarna_invoice_payment()
        return result
