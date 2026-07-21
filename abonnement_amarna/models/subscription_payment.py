# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AmarnaSubscriptionPayment(models.Model):
    _name = 'amarna.subscription.payment'
    _description = 'Paiement client'
    _order = 'payment_date desc, id desc'

    name = fields.Char(string='Référence', required=True, default='Nouveau', copy=False)
    subscription_id = fields.Many2one('amarna.subscription', string='Abonnement', ondelete='cascade')
    reservation_id = fields.Many2one('amarna.club.reservation', string='Réservation', ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Client', compute='_compute_partner', store=True)
    payment_date = fields.Date(string='Date de paiement', default=fields.Date.today, required=True)
    amount = fields.Monetary(string='Montant', required=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', compute='_compute_currency', store=True, readonly=True)
    method = fields.Selection([
        ('cash', 'Espèces'), ('card', 'Carte bancaire'), ('transfer', 'Virement'),
        ('mobile', 'Mobile money'), ('other', 'Autre'),
    ], string='Mode de paiement', required=True, default='cash')
    state = fields.Selection([
        ('draft', 'Brouillon'), ('confirmed', 'Confirmé'), ('cancelled', 'Annulé'),
    ], string='État', default='draft', required=True)
    reference = fields.Char(string='Référence externe')
    note = fields.Text(string='Notes')

    @api.depends('subscription_id.partner_id', 'reservation_id.partner_id')
    def _compute_partner(self):
        for payment in self:
            payment.partner_id = payment.subscription_id.partner_id or payment.reservation_id.partner_id

    @api.depends('subscription_id.currency_id', 'reservation_id.company_id.currency_id')
    def _compute_currency(self):
        for payment in self:
            payment.currency_id = payment.subscription_id.currency_id or payment.reservation_id.company_id.currency_id or self.env.company.currency_id

    @api.constrains('subscription_id', 'reservation_id', 'amount')
    def _check_target(self):
        for payment in self:
            if bool(payment.subscription_id) == bool(payment.reservation_id):
                raise ValidationError('Un paiement doit être lié à un abonnement ou à une réservation.')
            if payment.amount <= 0:
                raise ValidationError('Le montant du paiement doit être supérieur à zéro.')

    def action_confirm(self):
        self.write({'state': 'confirmed'})
        for payment in self:
            if payment.subscription_id:
                payment.subscription_id._sync_rfid_access()
            if payment.reservation_id:
                payment.reservation_id._sync_rfid_access()
        return True

    def action_cancel(self):
        self.write({'state': 'cancelled'})
        self.mapped('subscription_id')._sync_rfid_access()
        self.mapped('reservation_id')._sync_rfid_access()
