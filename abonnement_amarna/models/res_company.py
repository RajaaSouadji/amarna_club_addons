# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    """Club-wide settings, edited from Configuration > Club Amarna.

    Every business rule the club may want to change lives here or on the
    record it applies to (activity, plan, horse, pool reading...). The tablet
    app reads them through `amarna_app_config()` instead of keeping its own
    copy. Modules that add a rule extend `_amarna_app_config()`.
    """
    _inherit = 'res.company'

    amarna_default_tax_id = fields.Many2one(
        'account.tax', string='TVA par défaut des services',
        domain="[('type_tax_use', 'in', ('sale', 'all'))]",
        help="Appliquée automatiquement aux nouvelles activités et formules. "
             "Chaque activité et chaque formule peut ensuite avoir sa propre TVA.")
    amarna_opening_hour = fields.Float(
        string="Ouverture du club (h)", default=9.0,
        help="Heure décimale d'ouverture, 9.5 = 9h30.")
    amarna_closing_hour = fields.Float(
        string="Fermeture du club (h)", default=22.0,
        help="Heure décimale de fermeture, 22.0 = 22h00.")
    amarna_default_start_hour = fields.Float(
        string="Créneau par défaut : début (h)", default=9.0)
    amarna_default_end_hour = fields.Float(
        string="Créneau par défaut : fin (h)", default=10.0)
    amarna_expiry_warning_days = fields.Integer(
        string="Alerte fin d'abonnement (jours)", default=7,
        help="Un abonnement qui se termine dans moins de ce nombre de jours "
             "est signalé comme « bientôt expiré » sur la tablette.")
    amarna_checkin_guard_minutes = fields.Integer(
        string="Même carte lue deux fois (minutes)", default=5,
        help="Si la même carte est lue de nouveau dans ce délai, le passage n'est pas "
             "enregistré une seconde fois et aucune séance n'est retirée. 0 = pas de garde.")
    amarna_payment_reminder_days = fields.Integer(
        string="Relance des impayés (jours)", default=7,
        help="Un abonnement dont la facture reste impayée depuis ce nombre de jours déclenche une "
             "tâche « Relancer le paiement » pour son responsable, puis de nouveau à chaque période "
             "identique tant que rien n'est payé. 0 = pas de relance.")
    amarna_ticket_due_days = fields.Integer(
        string="Délai d'intervention par défaut (jours)", default=3,
        help="Échéance proposée automatiquement pour une nouvelle intervention.")
    amarna_booking_horizon_days = fields.Integer(
        string='Réservations possibles jusqu\'à (jours)', default=365,
        help="Nombre de jours à l'avance pendant lesquels on peut réserver.")
    amarna_default_people_count = fields.Integer(
        string='Nombre de personnes proposé', default=1,
        help="Valeur proposée à la création d'une réservation.")
    amarna_report_period_days = fields.Char(
        string='Périodes des rapports (jours)', default='7,30,90,365',
        help="Durées proposées dans les rapports de la tablette, en jours, "
             "séparées par des virgules. Ex : 7,30,90,365")
    amarna_report_default_days = fields.Integer(
        string='Période par défaut des rapports (jours)', default=30,
        help='Doit figurer dans la liste des périodes.')
    amarna_support_phone = fields.Char(string="Téléphone d'assistance")
    amarna_support_email = fields.Char(string="E-mail d'assistance")
    amarna_support_hours = fields.Char(string="Horaires d'assistance")

    @api.constrains('amarna_opening_hour', 'amarna_closing_hour',
                    'amarna_default_start_hour', 'amarna_default_end_hour')
    def _check_amarna_hours(self):
        for company in self:
            hours = (company.amarna_opening_hour, company.amarna_closing_hour,
                     company.amarna_default_start_hour, company.amarna_default_end_hour)
            if any(not 0 <= h <= 24 for h in hours):
                raise ValidationError('Les horaires doivent être compris entre 0 et 24 heures.')
            if company.amarna_closing_hour <= company.amarna_opening_hour:
                raise ValidationError("La fermeture doit être après l'ouverture du club.")
            if company.amarna_default_end_hour <= company.amarna_default_start_hour:
                raise ValidationError('Le créneau par défaut doit finir après son début.')

    @api.constrains('amarna_expiry_warning_days', 'amarna_ticket_due_days', 'amarna_checkin_guard_minutes',
                    'amarna_payment_reminder_days')
    def _check_amarna_days(self):
        for company in self:
            if (company.amarna_expiry_warning_days < 0 or company.amarna_ticket_due_days < 0
                    or company.amarna_checkin_guard_minutes < 0
                    or company.amarna_payment_reminder_days < 0):
                raise ValidationError('Les délais ne peuvent pas être négatifs.')

    @api.constrains('amarna_booking_horizon_days', 'amarna_default_people_count')
    def _check_amarna_reservations(self):
        for company in self:
            if company.amarna_booking_horizon_days < 1 or company.amarna_default_people_count < 1:
                raise ValidationError(
                    'La période de réservation et le nombre de personnes doivent être au moins 1.')

    def _amarna_report_periods(self):
        """Report periods as a list of positive ints, or raise ValidationError."""
        self.ensure_one()
        try:
            days = [int(part) for part in (self.amarna_report_period_days or '').split(',')
                    if part.strip()]
        except ValueError:
            raise ValidationError(
                'Les périodes des rapports doivent être des nombres de jours séparés par des virgules.')
        if not days or any(day < 1 for day in days):
            raise ValidationError('Indiquez au moins une période de rapport, en jours (1 minimum).')
        return days

    @api.constrains('amarna_report_period_days', 'amarna_report_default_days')
    def _check_amarna_reports(self):
        for company in self:
            if company.amarna_report_default_days not in company._amarna_report_periods():
                raise ValidationError(
                    'La période par défaut des rapports doit figurer dans la liste des périodes.')

    def _amarna_app_config(self):
        """Settings sent to the tablet app. Extend with `super()` and add a key."""
        self.ensure_one()
        tax = self.amarna_default_tax_id
        return {
            'club': {
                'name': self.name,
                'opening_hour': self.amarna_opening_hour,
                'closing_hour': self.amarna_closing_hour,
                'default_start_hour': self.amarna_default_start_hour,
                'default_end_hour': self.amarna_default_end_hour,
            },
            'currency': {
                'code': self.currency_id.name,
                'symbol': self.currency_id.symbol,
            },
            'tax': {
                'id': tax.id or None,
                'name': tax.name or None,
                'rate': tax.amount if tax else None,
            },
            'subscriptions': {
                'expiry_warning_days': self.amarna_expiry_warning_days,
            },
            'tickets': {
                'due_days': self.amarna_ticket_due_days,
            },
            'reservations': {
                'horizon_days': self.amarna_booking_horizon_days,
                'default_people_count': self.amarna_default_people_count,
            },
            'reports': {
                'period_days': self._amarna_report_periods(),
                'default_days': self.amarna_report_default_days,
            },
            'support': {
                'phone': self.amarna_support_phone or '',
                'email': self.amarna_support_email or '',
                'hours': self.amarna_support_hours or '',
            },
        }

    @api.model
    def amarna_app_config(self, company_id=None):
        """Called by the tablet after login. Returns the club settings."""
        company = self.browse(company_id) if company_id else self.env.company
        return company.sudo()._amarna_app_config()
