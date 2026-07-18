# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models

MOBILE_ID_RE = re.compile(r'\[Mobile ID:\s*([^\]]+)\]')
TYPE_RE = re.compile(r'^Type:\s*(\w+)', re.MULTILINE)


class AmarnaClubIntervention(models.Model):
    _name = 'amarna.club.intervention'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Intervention (incident ou maintenance)'
    _order = 'create_date desc'

    name = fields.Char(string='Titre', required=True, tracking=True)

    description = fields.Text(
        help="Description complète; l'application y inclut une ligne "
             "\"[Mobile ID: ...]\" qui sert de clé de synchronisation.",
    )

    mobile_id = fields.Char(
        string='ID mobile',
        index=True,
        copy=False,
        help="Identifiant du ticket côté tablette, extrait automatiquement "
             "de la description.",
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

    asset_id = fields.Many2one(
        'amarna.club.asset',
        string='Équipement',
    )

    date_due = fields.Datetime(string='Échéance', tracking=True)

    date_completed = fields.Datetime(string='Réalisé le')

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
        self._apply_mobile_values(vals)
        return super().write(vals)

    def _apply_mobile_values(self, vals):
        """Derive structured fields from the raw payload the tablet pushes."""
        description = vals.get('description')
        if description:
            if 'mobile_id' not in vals:
                match = MOBILE_ID_RE.search(description)
                if match:
                    vals['mobile_id'] = match.group(1).strip()
            if 'type' not in vals:
                match = TYPE_RE.search(description)
                if match:
                    ticket_type = match.group(1)
                    if ticket_type in ('anomaly', 'preventive', 'corrective'):
                        vals['type'] = ticket_type

        if vals.get('status') == 'resolved' and not vals.get('date_completed'):
            vals['date_completed'] = fields.Datetime.now()

        assignee = (vals.get('assigned_to') or '').strip()
        if assignee and 'user_id' not in vals:
            user = self.env['res.users'].search(
                [('name', 'ilike', assignee)], limit=1
            )
            if user:
                vals['user_id'] = user.id

    def action_take_over(self):
        self.write({'status': 'inProgress'})

    def action_resolve(self):
        self.write({'status': 'resolved'})

    def action_reopen(self):
        self.write({'status': 'open', 'date_completed': False})
