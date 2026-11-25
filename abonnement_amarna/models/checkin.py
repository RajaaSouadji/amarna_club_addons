# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AmarnaCheckin(models.Model):
    _name = 'amarna.checkin'
    _description = 'Check-in RFID'
    _order = 'checkin_datetime desc'

    partner_id = fields.Many2one('res.partner', string='Client', required=True)
    rfid_card_id = fields.Many2one('amarna.rfid.card', string='Carte RFID', required=True)
    activity_id = fields.Many2one('amarna.club.activity', string='Activité')
    checkin_datetime = fields.Datetime(string='Date et heure du passage', default=fields.Datetime.now, required=True)
    sessions_before = fields.Integer(string='Séances avant le scan')
    sessions_after = fields.Integer(string='Séances après le scan')
    subscription_id = fields.Many2one('amarna.subscription', string='Abonnement')

    @api.depends('partner_id', 'checkin_datetime')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s – %s' % (
                rec.partner_id.name or 'Passage',
                fields.Datetime.context_timestamp(rec, rec.checkin_datetime).strftime('%d/%m/%Y %H:%M')
                if rec.checkin_datetime else '')
