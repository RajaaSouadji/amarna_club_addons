# -*- coding: utf-8 -*-
import re
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError

# Description lines written by the tablet before version 1.1 of this module.
# They are only read when the structured fields are absent (legacy rows and
# the maintenance.request migration).
MOBILE_ID_RE = re.compile(r'\[Mobile ID:\s*([^\]]+)\]')
TYPE_RE = re.compile(r'^Type:\s*(\w+)', re.MULTILINE)

TYPE_VALUES = ('anomaly', 'preventive', 'corrective')
PRIORITY_VALUES = ('low', 'medium', 'high', 'critical')
STATUS_VALUES = ('open', 'inProgress', 'resolved')


class AmarnaClubIntervention(models.Model):
    _name = 'amarna.club.intervention'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Intervention (incident ou maintenance)'
    _order = 'create_date desc'

    name = fields.Char(string='Titre', required=True, tracking=True)

    description = fields.Text(
        help="Description complète saisie sur la tablette.",
    )

    mobile_id = fields.Char(
        string='ID mobile',
        index=True,
        copy=False,
        help="Identifiant du ticket côté tablette. C'est la clé de "
             "synchronisation : la tablette crée ou met à jour le ticket "
             "portant cet identifiant.",
    )

    # Selection keys match the app's TicketType enum names.
    type = fields.Selection(
        [
            ('anomaly', 'Incident'),
            ('preventive', 'Maintenance préventive'),
            ('corrective', 'Maintenance corrective'),
        ],
        default='anomaly',
        tracking=True,
    )

    # Selection keys match the app's TicketPriority enum names.
    priority = fields.Selection(
        [
            ('low', 'Faible'),
            ('medium', 'Moyen'),
            ('high', 'Élevé'),
            ('critical', 'Critique'),
        ],
        default='medium',
        tracking=True,
    )

    # Selection keys match the app's TicketStatus enum names.
    status = fields.Selection(
        [
            ('open', 'Ouvert'),
            ('inProgress', 'En cours'),
            ('resolved', 'Résolu'),
        ],
        default='open',
        tracking=True,
    )

    mobile_activity_code = fields.Char(
        string='Code activité mobile',
    )

    activity_id = fields.Many2one(
        'amarna.club.activity',
        string='Activité',
        compute='_compute_activity_id',
        store=True,
        readonly=False,
        tracking=True,
    )

    mobile_asset_code = fields.Char(
        string='Code équipement mobile',
        help="Code de l'équipement concerné, tel que dans la tablette.",
    )

    asset_id = fields.Many2one(
        'amarna.club.asset',
        string='Équipement',
    )

    date_due = fields.Datetime(
        string='Échéance (UTC)', tracking=True,
        default=lambda self: fields.Datetime.now() + timedelta(
            days=self.env.company.amarna_ticket_due_days),
        help="Proposée à partir du délai défini dans la configuration du club.")

    date_completed = fields.Datetime(string='Réalisé le (UTC)')

    assigned_to = fields.Char(
        string='Technicien (mobile)',
        help='Nom du technicien tel que saisi sur la tablette; le lien '
             'utilisateur est résolu automatiquement si possible.',
    )

    user_id = fields.Many2one(
        'res.users',
        string='Technicien',
        tracking=True,
    )

    is_overdue = fields.Boolean(
        string='En retard',
        compute='_compute_is_overdue',
    )

    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
    )

    @api.depends('mobile_activity_code')
    def _compute_activity_id(self):
        Activity = self.env['amarna.club.activity']
        for rec in self:
            if rec.mobile_activity_code:
                rec.activity_id = Activity._find_by_mobile_code(
                    rec.mobile_activity_code
                )
            elif not rec.activity_id:
                rec.activity_id = False

    @api.depends('date_due', 'status')
    def _compute_is_overdue(self):
        now = fields.Datetime.now()
        for rec in self:
            rec.is_overdue = bool(
                rec.date_due and rec.status != 'resolved'
                and rec.date_due < now
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._apply_mobile_values(vals)
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)
        self._apply_mobile_values(vals)
        result = super().write(vals)
        # Stamp the completion date once, on the first transition to resolved.
        for rec in self.filtered(lambda r: r.status == 'resolved' and not r.date_completed):
            rec.date_completed = fields.Datetime.now()
        return result

    def _apply_mobile_values(self, vals):
        """Derive structured fields from the payload pushed by the tablet.

        Explicit values always win; the description is only parsed when the
        structured field is missing (legacy rows).
        """
        description = vals.get('description')
        if description:
            if not vals.get('mobile_id'):
                match = MOBILE_ID_RE.search(description)
                if match:
                    vals['mobile_id'] = match.group(1).strip()
            if 'type' not in vals:
                match = TYPE_RE.search(description)
                if match and match.group(1) in TYPE_VALUES:
                    vals['type'] = match.group(1)

        # Reject unknown enum values loudly: silently dropping them would make
        # the tablet believe a status was saved when it was not.
        for field_name, allowed in (('type', TYPE_VALUES),
                                    ('priority', PRIORITY_VALUES),
                                    ('status', STATUS_VALUES)):
            if vals.get(field_name) and vals[field_name] not in allowed:
                raise ValidationError(
                    "Valeur invalide pour %s : « %s »." % (field_name, vals[field_name]))

        if vals.get('mobile_asset_code') and 'asset_id' not in vals:
            asset = self.env['amarna.club.asset'].search(
                [('code', '=', vals['mobile_asset_code'])], limit=1)
            vals['asset_id'] = asset.id or False

        assignee = (vals.get('assigned_to') or '').strip()
        if assignee and 'user_id' not in vals:
            Users = self.env['res.users']
            user = (Users.search([('name', '=', assignee)], limit=1)
                    or Users.search([('name', 'ilike', assignee)], limit=1))
            vals['user_id'] = user.id or False

    def action_take_over(self):
        self.write({'status': 'inProgress'})

    def action_resolve(self):
        self.write({'status': 'resolved'})

    def action_reopen(self):
        self.write({'status': 'open', 'date_completed': False})
