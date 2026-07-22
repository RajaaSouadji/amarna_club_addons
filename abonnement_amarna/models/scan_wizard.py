# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class AmarnaScanWizard(models.TransientModel):
    _name = 'amarna.scan.wizard'
    _description = 'Scan de carte RFID - Contrôle accès'

    rfid_uid = fields.Char(string='Identifiant RFID', required=True)
    card_id = fields.Many2one('amarna.rfid.card', string='Carte', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Membre', readonly=True)
    subscription_id = fields.Many2one('amarna.subscription', string='Abonnement actif', readonly=True)
    remaining_sessions = fields.Integer(string='Séances restantes', readonly=True)
    expiration_date = fields.Date(string='Expiration abonnement', readonly=True)
    result_state = fields.Selection([
        ('pending', 'En attente de scan'),
        ('ok', 'Accès autorisé'),
        ('denied', 'Accès refusé'),
    ], default='pending', string='Résultat', readonly=True)
    result_message = fields.Text(string='Message', readonly=True)

    @api.onchange('rfid_uid')
    def _onchange_rfid_uid(self):
        self.card_id = self.partner_id = self.subscription_id = False
        self.remaining_sessions = 0
        self.expiration_date = False
        self.result_state = 'pending'
        self.result_message = False

    def action_scan(self):
        self.ensure_one()
        uid = (self.rfid_uid or '').strip()
        if not uid:
            raise UserError('Veuillez saisir l’UID de la carte.')

        card = self.env['amarna.rfid.card'].search([('name', '=', uid)], limit=1)
        if not card:
            return self._scan_error('Carte inconnue.')
        self.card_id = card
        self.partner_id = card.partner_id

        if not card.active or card.state != 'active':
            return self._scan_error('Cette carte est désactivée.')

        today = fields.Date.today()
        subscriptions = self.env['amarna.subscription'].search([
            ('rfid_card_id', '=', card.id),
        ], order='expiration_date desc, id desc')
        if not subscriptions:
            return self._scan_error('Aucun abonnement actif.')

        valid_subscriptions = subscriptions.filtered(
            lambda sub: sub.active
            and sub.state == 'sale'
            and sub.start_date <= today
            and (not sub.expiration_date or sub.expiration_date >= today)
        )
        if not valid_subscriptions:
            if subscriptions.filtered(lambda sub: sub.expiration_date and sub.expiration_date < today):
                return self._scan_error('Abonnement expiré.')
            return self._scan_error('Aucun abonnement actif.')

        subscription = valid_subscriptions[0]
        self.subscription_id = subscription
        self.expiration_date = subscription.expiration_date
        before = subscription.remaining_sessions
        if before <= 0:
            return self._scan_error('Aucune séance restante.')

        subscription.write({'remaining_sessions': before - 1})
        self.remaining_sessions = before - 1
        self.env['amarna.checkin'].create({
            'partner_id': card.partner_id.id,
            'card_id': card.id,
            'subscription_id': subscription.id,
            'sessions_before': before,
            'sessions_after': before - 1,
        })
        self.result_state = 'ok'
        self.result_message = 'Accès autorisé. Il reste %s séance(s).' % (before - 1)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Accès autorisé',
                'message': self.result_message,
                'type': 'success',
                'sticky': False,
            },
        }

    def _scan_error(self, message):
        self.result_state = 'denied'
        self.result_message = message
        return False
