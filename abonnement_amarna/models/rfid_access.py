# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AmarnaRfidAccess(models.Model):
    _name = 'amarna.rfid.access'
    _description = 'Autorisation d’accès RFID'
    _order = 'start_datetime desc'

    name = fields.Char(string='Référence', required=True, default='Nouveau', copy=False)
    card_id = fields.Many2one('amarna.rfid.card', string='Carte RFID', required=True, ondelete='cascade', index=True)
    partner_id = fields.Many2one(related='card_id.partner_id', store=True, readonly=True)
    subscription_id = fields.Many2one('amarna.subscription', string='Abonnement', ondelete='cascade')
    reservation_id = fields.Many2one('amarna.club.reservation', string='Réservation', ondelete='cascade')
    start_datetime = fields.Datetime(string='Début d’accès', required=True)
    end_datetime = fields.Datetime(string='Fin d’accès', required=True)
    state = fields.Selection([
        ('scheduled', 'Planifiée'), ('active', 'Active'), ('expired', 'Expirée'), ('cancelled', 'Annulée'),
    ], default='scheduled', required=True)
    source = fields.Selection([('subscription', 'Abonnement'), ('reservation', 'Réservation')], required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)

    @api.constrains('subscription_id', 'reservation_id', 'source', 'start_datetime', 'end_datetime')
    def _check_access(self):
        for access in self:
            if access.start_datetime >= access.end_datetime:
                raise ValidationError('La fin de l’accès RFID doit être postérieure au début.')
            if bool(access.subscription_id) == bool(access.reservation_id):
                raise ValidationError('Une autorisation RFID doit être liée à un abonnement ou à une réservation, mais pas aux deux.')
            expected = 'subscription' if access.subscription_id else 'reservation'
            if access.source != expected:
                raise ValidationError('La source de l’autorisation RFID est incohérente.')

    @api.model
    def cron_sync_access(self):
        now = fields.Datetime.now()
        self.search([('state', '=', 'active'), ('end_datetime', '<', now)]).write({'state': 'expired', 'active': False})
        self.search([('state', '=', 'scheduled'), ('start_datetime', '<=', now), ('end_datetime', '>=', now)]).write({'state': 'active'})
        self.env['amarna.rfid.card'].search([])._sync_access_state()
        return True

