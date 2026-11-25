# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class AmarnaSubscriptionCloseReason(models.Model):
    """Why a member stops (moved away, price, injury...): used to understand churn."""
    _name = 'amarna.subscription.close.reason'
    _description = "Motif d'arrêt d'abonnement"
    _order = 'sequence, name'

    name = fields.Char(string='Motif', required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)


class AmarnaSubscriptionFreeze(models.TransientModel):
    """Suspend a subscription (travel, injury): no access meanwhile, and the end
    date moves by the same number of days so the member loses nothing."""
    _name = 'amarna.subscription.freeze'
    _description = 'Suspendre un abonnement'

    subscription_id = fields.Many2one(
        'amarna.subscription', string='Abonnement', required=True, ondelete='cascade')
    date_from = fields.Date(string='Du', required=True, default=fields.Date.context_today)
    date_to = fields.Date(string="Jusqu'au", required=True)
    days = fields.Integer(string='Jours suspendus', compute='_compute_days')

    @api.depends('date_from', 'date_to')
    def _compute_days(self):
        for rec in self:
            rec.days = (rec.date_to - rec.date_from).days + 1 if rec.date_from and rec.date_to else 0

    def action_freeze(self):
        self.ensure_one()
        sub = self.subscription_id
        if self.date_to < self.date_from:
            raise ValidationError("La fin de la suspension doit suivre son début.")
        if sub.state != 'confirmed':
            raise UserError("Seul un abonnement confirmé peut être suspendu.")
        if sub.freeze_end and sub.freeze_end >= fields.Date.context_today(self):
            raise UserError("Une suspension est déjà prévue ou en cours (jusqu'au %s)." % sub.freeze_end)
        sub.write({
            'freeze_start': self.date_from, 'freeze_end': self.date_to,
            'expiration_date': sub.expiration_date + timedelta(days=self.days)})
        sub.message_post(
            body="Abonnement suspendu du %s au %s : la date de fin est repoussée de %d jour(s)." % (
                self.date_from, self.date_to, self.days),
            subtype_xmlid='mail.mt_note')
        return {'type': 'ir.actions.act_window_close'}


class ResPartner(models.Model):
    """Member card: what the front desk needs to know about a person."""
    _inherit = 'res.partner'

    amarna_is_member = fields.Boolean(
        string='Membre du club', default=False,
        help="Coché automatiquement quand la fiche est créée depuis le menu Membres. "
             "Un contact qui a un abonnement est aussi un membre.")
    amarna_birth_date = fields.Date(string='Date de naissance')
    amarna_is_minor = fields.Boolean(string='Mineur', compute='_compute_amarna_is_minor')
    amarna_guardian_id = fields.Many2one(
        'res.partner', string='Responsable légal',
        help="Parent ou tuteur d'un membre mineur.")
    amarna_medical_certificate_end = fields.Date(
        string='Certificat médical valable jusqu\'au')
    amarna_emergency_name = fields.Char(string="Contact d'urgence")
    amarna_emergency_phone = fields.Char(string="Téléphone d'urgence")
    amarna_subscription_ids = fields.One2many(
        'amarna.subscription', 'partner_id', string='Abonnements Amarna')
    amarna_subscription_count = fields.Integer(compute='_compute_amarna_subscription_count')
    amarna_rfid_card_ids = fields.One2many(
        'amarna.rfid.card', 'partner_id', string='Carte RFID',
        help="La carte d'accès du membre : scannez-la ici une fois, ses abonnements et "
             "réservations l'utilisent ensuite d'eux-mêmes.")

    @api.depends('amarna_birth_date')
    def _compute_amarna_is_minor(self):
        today = fields.Date.context_today(self)
        for rec in self:
            born = rec.amarna_birth_date
            rec.amarna_is_minor = bool(born and (
                today.year - born.year - ((today.month, today.day) < (born.month, born.day))) < 18)

    @api.depends('amarna_subscription_ids')
    def _compute_amarna_subscription_count(self):
        counts = dict(self.env['amarna.subscription']._read_group(
            [('partner_id', 'in', self.ids)], ['partner_id'], ['__count']))
        for rec in self:
            rec.amarna_subscription_count = counts.get(rec, 0)

    def action_view_amarna_subscriptions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': 'Abonnements',
            'res_model': 'amarna.subscription', 'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id}}
