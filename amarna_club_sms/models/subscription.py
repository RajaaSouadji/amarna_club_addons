# -*- coding: utf-8 -*-
import logging
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AmarnaSubscription(models.Model):
    _inherit = 'amarna.subscription'

    expiry_sms_for = fields.Date(
        string="SMS de fin envoyé pour le", copy=False,
        help="Date de fin pour laquelle le SMS a été envoyé. Une fois l'abonnement renouvelé, la date "
             "de fin change : le SMS de la période suivante peut partir.")

    def _expiry_sms_body(self):
        self.ensure_one()
        template = self.company_id.amarna_sms_expiry_body or ''
        values = {
            'name': self.partner_id.name or '',
            'plan': self.plan_id.name or '',
            'date': self.expiration_date.strftime('%d/%m/%Y') if self.expiration_date else '',
            'club': self.company_id.name or '',
        }
        try:
            return template.format(**values)
        except (KeyError, IndexError, ValueError):
            # a word between braces the club typed by mistake: send the text as it is
            return template

    def _send_expiry_sms(self):
        """Send the end-of-subscription SMS of this subscription. Returns True when one was queued."""
        self.ensure_one()
        partner = self.partner_id
        number = partner._phone_format(fname='phone') or partner.phone if partner else False
        if not number:
            self.message_post(
                body="SMS de fin d'abonnement non envoyé : %s n'a pas de numéro de téléphone." % partner.name,
                subtype_xmlid='mail.mt_note')
            return False
        self._message_sms(
            self._expiry_sms_body(), partner_ids=partner.ids, sms_pid_to_number={partner.id: number})
        return True

    def action_send_expiry_sms(self):
        """Send the reminder now, by hand (also the way to try it out before switching it on)."""
        for sub in self:
            if not sub._send_expiry_sms():
                raise UserError("%s n'a pas de numéro de téléphone." % sub.partner_id.name)
        return True

    @api.model
    def cron_expiry_sms(self):
        """Daily: SMS to the members whose subscription ends in N days, once per end date."""
        for company in self.env['res.company'].search([('amarna_sms_expiry_enabled', '=', True)]):
            target = fields.Date.context_today(self) + timedelta(days=company.amarna_sms_expiry_days)
            subscriptions = self.search([
                ('company_id', '=', company.id), ('state', '=', 'confirmed'), ('active', '=', True),
                ('expiration_date', '=', target),
            ]).filtered(lambda s: s.expiry_sms_for != s.expiration_date and not s.is_frozen)
            for sub in subscriptions:
                try:
                    with self.env.cr.savepoint():
                        sub._send_expiry_sms()
                except Exception:  # one bad number must not stop the others
                    _logger.exception("SMS de fin d'abonnement impossible pour %s", sub.name)
                # marked even when it failed: the failure is in the chatter, no daily retry spam
                sub.expiry_sms_for = sub.expiration_date
        return True
