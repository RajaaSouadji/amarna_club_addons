# -*- coding: utf-8 -*-
from datetime import timedelta

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

    # ---------------------------------------------------------- Reader desk

    @api.model
    def scan_card(self, code, subscription_id=None):
        """One-step reading of a card at the desk: check, and record the passage.

        Called by the scan screen each time the reader types a number. Returns a
        dict for the screen: ``status`` is ``success`` (passage recorded),
        ``duplicate`` (the same card was just read, nothing taken again),
        ``denied`` (with the reason) or ``choose`` (the member has several valid
        subscriptions: the screen asks which one to use, then calls again with
        ``subscription_id``)."""
        code = (code or '').strip()
        card = self.env['amarna.rfid.card'].search([('name', '=ilike', code)], limit=1) if code else None
        if not card:
            return {'status': 'denied', 'message': "Carte inconnue : %s" % code if code else "Aucun numéro lu."}
        result = {'card': card.name, 'member': self._scan_member(card.partner_id)}
        if card.restriction:
            label = dict(card._fields['restriction'].selection)[card.restriction]
            return dict(result, status='denied', message="Carte %s : accès refusé." % label.lower())
        subscriptions = self.env['amarna.subscription'].search(
            [('rfid_card_id', '=', card.id), ('active', '=', True)],
            order='activity_id, start_date desc')
        if not subscriptions:
            return dict(result, status='denied', message="Aucun abonnement actif pour cette carte.")
        if subscription_id:
            sub = subscriptions.filtered(lambda s: s.id == subscription_id)[:1]
        else:
            valid = subscriptions.filtered(lambda s: not s._scan_denial())
            if len(valid) > 1:
                return dict(result, status='choose', message="Plusieurs abonnements valides : choisissez.",
                            choices=[{'id': s.id, 'label': s.activity_id.name or s.name,
                                      'remaining': self._sessions_label(s)} for s in valid])
            sub = valid or subscriptions[:1]
        if not sub:
            return dict(result, status='denied', message="Abonnement introuvable pour cette carte.")
        denial = sub._scan_denial()
        if denial:
            return dict(result, status='denied', message=denial, subscription=self._scan_subscription(sub))
        minutes = self.env.company.amarna_checkin_guard_minutes
        last = self.search([('rfid_card_id', '=', card.id), ('subscription_id', '=', sub.id)], limit=1)
        if minutes and last and last.checkin_datetime > fields.Datetime.now() - timedelta(minutes=minutes):
            at = fields.Datetime.context_timestamp(self, last.checkin_datetime).strftime('%H:%M')
            return dict(result, status='duplicate', subscription=self._scan_subscription(sub),
                        message="Déjà enregistré à %s : aucune séance retirée." % at)
        sub._record_checkin(card)
        return dict(result, status='success', message="Accès autorisé.",
                    subscription=self._scan_subscription(sub))

    @api.model
    def _sessions_label(self, sub):
        return 'Illimité' if sub.is_unlimited else str(sub.remaining_sessions)

    @api.model
    def _scan_member(self, partner):
        return {'id': partner.id, 'name': partner.name, 'phone': partner.phone or ''} if partner else {}

    @api.model
    def _scan_subscription(self, sub):
        return {
            'id': sub.id, 'activity': sub.activity_id.name or '', 'plan': sub.plan_id.name or '',
            'remaining': self._sessions_label(sub),
            'expires': fields.Date.to_string(sub.expiration_date) if sub.expiration_date else '',
        }
