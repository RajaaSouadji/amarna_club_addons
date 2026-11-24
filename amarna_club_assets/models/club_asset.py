# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models


class AmarnaClubAsset(models.Model):
    _name = 'amarna.club.asset'
    _inherit = ['mail.thread', 'amarna.activity.mixin']
    _description = 'Équipement du club'
    _order = 'activity_id, name'

    name = fields.Char(required=True, tracking=True)

    code = fields.Char(
        string='Code mobile',
        index=True,
        copy=False,
        help="Identifiant de l'asset dans l'application tablette "
             "(ex: asset-pool-filter-01).",
    )

    serial_number = fields.Char(string='Numéro de série')

    category_id = fields.Many2one(
        'amarna.club.asset.category', string='Catégorie', tracking=True)

    # The tablet reads this label; it follows the category chosen in Odoo.
    category = fields.Char(
        string='Libellé de catégorie',
        compute='_compute_category', store=True, readonly=False,
        help="Libellé affiché dans l'application "
             "(ex: Équipement Piscine, Arme de Poing).",
    )

    location = fields.Char(string='Emplacement')
    staff_id = fields.Many2one(
        'amarna.club.staff', string='Responsable', tracking=True,
        compute='_compute_staff', store=True, readonly=False)
    purchase_date = fields.Date(string="Date d'achat")
    purchase_value = fields.Monetary(string="Valeur d'achat", currency_field='currency_id')
    supplier_id = fields.Many2one('res.partner', string='Fournisseur')
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)
    maintenance_interval_days = fields.Integer(
        string='Entretien préventif tous les (jours)',
        compute='_compute_interval', store=True, readonly=False,
        help="0 = pas d'entretien planifié. Repris de la catégorie.")
    usage_count = fields.Integer(
        string="Nombre d'utilisations", readonly=True, copy=False,
        help="Incrémenté chaque fois que l'équipement passe en utilisation.")
    notes = fields.Html(string='Notes')

    service_ids = fields.One2many(
        'amarna.club.asset.service', 'asset_id', string="Journal d'entretien")
    contract_ids = fields.One2many(
        'amarna.club.asset.contract', 'asset_id', string='Contrats & garanties')
    weapon_log_ids = fields.One2many(
        'amarna.club.weapon.log', 'asset_id', string="Registre d'armurerie")
    service_count = fields.Integer(compute='_compute_counts')
    contract_count = fields.Integer(compute='_compute_counts')
    weapon_log_count = fields.Integer(compute='_compute_counts')
    total_service_cost = fields.Monetary(
        string="Coût d'entretien cumulé", compute='_compute_counts',
        currency_field='currency_id')
    maintenance_due = fields.Boolean(
        string='Entretien à faire', compute='_compute_maintenance_due',
        search='_search_maintenance_due')
    weapon_state = fields.Selection(
        [('in_armory', "À l'armurerie"), ('issued', 'Remise')],
        string="État de l'arme", compute='_compute_weapon_state')

    # Selection keys match the app's AssetStatus enum names.
    status = fields.Selection(
        [
            ('available', 'Disponible'),
            ('inUse', 'En utilisation'),
            ('maintenance', 'En maintenance'),
            ('broken', 'Hors-service'),
        ],
        default='available',
        string='Statut',
        tracking=True,
    )

    last_maintenance = fields.Datetime(string='Dernière maintenance')

    next_maintenance = fields.Datetime(
        string='Prochaine maintenance',
        help='Pour les armes, sert de date de nettoyage due.',
    )

    image_url = fields.Char(string='Image (URL)')

    specs_json = fields.Text(
        string='Spécifications techniques (JSON)',
        help='Dictionnaire JSON clé/valeur affiché sur la fiche asset '
             'de la tablette.',
    )

    is_weapon = fields.Boolean(
        string='Arme',
        help="Cochez pour les armes : elles apparaissent dans l'armurerie de "
             "la tablette et suivent l'intervalle de nettoyage du club.",
    )

    in_use_since = fields.Datetime(
        string='En utilisation depuis',
        readonly=True,
        copy=False,
        help="Renseigné automatiquement quand l'équipement passe en "
             "« En utilisation » (ex. un terrain de padel).",
    )

    active = fields.Boolean(default=True)

    @api.depends('category_id')
    def _compute_category(self):
        for rec in self:
            if rec.category_id:
                rec.category = rec.category_id.name

    @api.depends('category_id')
    def _compute_staff(self):
        for rec in self:
            if rec.category_id.staff_id and not rec.staff_id:
                rec.staff_id = rec.category_id.staff_id

    @api.depends('category_id')
    def _compute_interval(self):
        for rec in self:
            if rec.category_id.maintenance_interval_days:
                rec.maintenance_interval_days = rec.category_id.maintenance_interval_days

    @api.depends('service_ids.cost', 'contract_ids', 'weapon_log_ids')
    def _compute_counts(self):
        for rec in self:
            rec.service_count = len(rec.service_ids)
            rec.contract_count = len(rec.contract_ids)
            rec.weapon_log_count = len(rec.weapon_log_ids)
            rec.total_service_cost = sum(rec.service_ids.mapped('cost'))

    @api.depends('next_maintenance')
    def _compute_maintenance_due(self):
        now = fields.Datetime.now()
        for rec in self:
            rec.maintenance_due = bool(rec.next_maintenance and rec.next_maintenance <= now)

    def _search_maintenance_due(self, operator, value):
        if operator not in ('=', '!='):
            return NotImplemented
        due = (operator == '=') == bool(value)
        now = fields.Datetime.now()
        if due:
            return [('next_maintenance', '!=', False), ('next_maintenance', '<=', now)]
        return ['|', ('next_maintenance', '=', False), ('next_maintenance', '>', now)]

    @api.depends('weapon_log_ids.state', 'is_weapon')
    def _compute_weapon_state(self):
        for rec in self:
            if not rec.is_weapon:
                rec.weapon_state = False
            else:
                issued = any(log.state == 'issued' for log in rec.weapon_log_ids)
                rec.weapon_state = 'issued' if issued else 'in_armory'

    def _next_due_from(self, last):
        """Next preventive date after an intervention done on `last`."""
        self.ensure_one()
        days = self.maintenance_interval_days
        if not days and self.is_weapon:
            days = self.env.company.amarna_weapon_cleaning_days
        return last + timedelta(days=days) if days else False

    def _refresh_maintenance_dates(self):
        """Last/next maintenance follow the journal (the tablet reads both)."""
        for rec in self:
            services = rec.service_ids.sorted(lambda s: (s.date, s.id), reverse=True)
            if not services:
                continue
            last = fields.Datetime.to_datetime(services[0].date)
            vals = {'last_maintenance': last}
            nxt = rec._next_due_from(last)
            if nxt:
                vals['next_maintenance'] = nxt
            rec.with_context(amarna_skip_service_log=True).write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('status') == 'inUse' and 'in_use_since' not in vals:
                vals['in_use_since'] = fields.Datetime.now()
                vals.setdefault('usage_count', 1)
        return super().create(vals_list)

    def write(self, vals):
        if 'status' in vals and 'in_use_since' not in vals:
            if vals['status'] == 'inUse':
                # Only items that were not already in use start a new session.
                starting = self.filtered(lambda asset: asset.status != 'inUse')
                others = self - starting
                if others:
                    super(AmarnaClubAsset, others).write(vals)
                for asset in starting:
                    super(AmarnaClubAsset, asset).write(dict(
                        vals, in_use_since=fields.Datetime.now(),
                        usage_count=asset.usage_count + 1))
                return True
            vals = dict(vals, in_use_since=False)
        result = super().write(vals)
        if 'last_maintenance' in vals and not self.env.context.get('amarna_skip_service_log'):
            self._log_tablet_maintenance()
        return result

    def _log_tablet_maintenance(self):
        """The tablet only pushes `last_maintenance` (a cleaning just done):
        keep a journal line so the history is not lost, and move the next date."""
        Service = self.env['amarna.club.asset.service']
        for rec in self.filtered('last_maintenance'):
            day = fields.Date.to_date(rec.last_maintenance)
            if Service.search_count([('asset_id', '=', rec.id), ('date', '=', day)]):
                continue
            Service.create({
                'asset_id': rec.id, 'date': day,
                'service_type': 'cleaning' if rec.is_weapon else 'preventive',
                'description': 'Enregistré depuis la tablette'})

    # ------------------------------------------------------------ buttons
    def action_view_services(self):
        return self._open_related('amarna.club.asset.service', "Journal d'entretien")

    def action_view_contracts(self):
        return self._open_related('amarna.club.asset.contract', 'Contrats & garanties')

    def action_view_weapon_log(self):
        return self._open_related('amarna.club.weapon.log', "Registre d'armurerie")

    def _open_related(self, model, name):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': name, 'res_model': model,
            'view_mode': 'list,form', 'domain': [('asset_id', '=', self.id)],
            'context': {'default_asset_id': self.id},
        }

    def action_issue_weapon(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': 'Remettre une arme',
            'res_model': 'amarna.club.weapon.log', 'view_mode': 'form',
            'target': 'new', 'context': {'default_asset_id': self.id},
        }
