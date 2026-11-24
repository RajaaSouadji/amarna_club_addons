# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AmarnaClubHorse(models.Model):
    _name = 'amarna.club.horse'
    _inherit = ['mail.thread']
    _description = 'Cheval du club'
    _order = 'box_number, name'

    name = fields.Char(required=True, tracking=True)
    image_1920 = fields.Image(string='Photo', max_width=1024, max_height=1024)
    birth_date = fields.Date(string='Date de naissance')
    sex = fields.Selection(
        [('mare', 'Jument'), ('gelding', 'Hongre'), ('stallion', 'Étalon')], string='Sexe')
    coat = fields.Char(string='Robe')
    height_cm = fields.Integer(string='Taille (cm)')
    chip_number = fields.Char(string='N° de puce', copy=False)
    passport_number = fields.Char(string='N° de passeport (UELN)', copy=False)
    owner_id = fields.Many2one('res.partner', string='Propriétaire', tracking=True)
    is_boarder = fields.Boolean(
        string='Pensionnaire',
        help="Cheval appartenant à un propriétaire extérieur, en pension à l'écurie.")
    box_id = fields.Many2one('amarna.club.horse.box', string='Box / paddock', tracking=True)
    care_ids = fields.One2many('amarna.club.horse.care', 'horse_id', string='Soins')
    feed_ids = fields.One2many('amarna.club.horse.feed', 'horse_id', string='Ration')
    boarding_ids = fields.One2many('amarna.club.horse.boarding', 'horse_id', string='Pensions')
    care_count = fields.Integer(compute='_compute_counts')
    boarding_count = fields.Integer(compute='_compute_counts')
    care_cost_total = fields.Monetary(
        string='Frais de soins', compute='_compute_counts', currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)
    notes = fields.Html(string='Notes')

    code = fields.Char(
        string='Code mobile',
        index=True,
        copy=False,
        help="Identifiant du cheval dans l'application tablette (ex: h1).",
    )

    breed = fields.Char(string='Race')

    age_declared = fields.Integer(string='Âge (saisi)')

    # The tablet reads `age`: it follows the birth date when there is one.
    age = fields.Integer(
        string='Âge', compute='_compute_age', inverse='_inverse_age')

    # The tablet reads the box label; it follows the box chosen in Odoo.
    box_number = fields.Char(
        string='Libellé du box', compute='_compute_box_number', store=True, readonly=False)

    # Selection keys match the app's HorseStatus enum names.
    status = fields.Selection(
        [
            ('available', 'Disponible'),
            ('resting', 'Au repos'),
            ('injured', 'Blessé'),
        ],
        default='available',
        string='Statut',
    )

    fatigue = fields.Float(
        string='Fatigue (0-1)',
        help='Niveau de fatigue entre 0.0 (reposé) et 1.0 (épuisé), '
             "tel qu'affiché par la jauge de l'application.",
    )

    fatigue_pct = fields.Float(
        string='Fatigue (%)',
        compute='_compute_fatigue_pct',
    )

    # Summary of the feeding plan lines, as the tablet shows it.
    diet = fields.Char(
        string='Alimentation', compute='_compute_diet', store=True, readonly=False)

    vet_note = fields.Text(string='Note vétérinaire')

    next_vet_visit = fields.Datetime(string='Prochaine visite vétérinaire')

    # The three dates below follow the care journal (latest entry of each
    # kind); they can still be typed for a horse that has no journal yet.
    last_farrier = fields.Date(
        string='Dernier maréchal-ferrant', compute='_compute_last_care',
        store=True, readonly=False)

    last_vaccine = fields.Date(
        string='Dernier vaccin', compute='_compute_last_care',
        store=True, readonly=False)

    last_deworming = fields.Date(
        string='Dernier vermifuge', compute='_compute_last_care',
        store=True, readonly=False)

    farrier_due = fields.Boolean(
        string='Ferrage à prévoir',
        compute='_compute_care_due',
        search='_search_farrier_due',
        help="Ferrage recommandé selon l'intervalle défini dans la configuration de l'écurie.",
    )

    deworming_due = fields.Boolean(
        string='Vermifuge à prévoir',
        compute='_compute_care_due',
        search='_search_deworming_due',
        help="Vermifuge recommandé selon l'intervalle défini dans la configuration de l'écurie.",
    )

    active = fields.Boolean(default=True)

    @api.depends('birth_date', 'age_declared')
    def _compute_age(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.birth_date:
                born = rec.birth_date
                rec.age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
            else:
                rec.age = rec.age_declared

    def _inverse_age(self):
        for rec in self:
            if not rec.birth_date:
                rec.age_declared = rec.age

    @api.depends('box_id.name')
    def _compute_box_number(self):
        for rec in self:
            if rec.box_id:
                rec.box_number = rec.box_id.name

    @api.depends('feed_ids.meal', 'feed_ids.feed_name', 'feed_ids.quantity', 'feed_ids.unit')
    def _compute_diet(self):
        meals = dict(self.env['amarna.club.horse.feed']._fields['meal'].selection)
        for rec in self:
            if rec.feed_ids:
                rec.diet = ' ; '.join(
                    '%s : %s %g %s' % (meals[f.meal], f.feed_name, f.quantity, f.unit or '')
                    for f in rec.feed_ids.sorted(lambda f: (f.sequence, f.id)))

    @api.depends('care_ids.date', 'care_ids.care_type')
    def _compute_last_care(self):
        mapping = {'farrier': 'last_farrier', 'vaccine': 'last_vaccine', 'deworming': 'last_deworming'}
        for rec in self:
            for care_type, fname in mapping.items():
                dates = rec.care_ids.filtered(lambda c: c.care_type == care_type).mapped('date')
                if dates:
                    rec[fname] = max(dates)

    @api.depends('care_ids.cost', 'boarding_ids')
    def _compute_counts(self):
        for rec in self:
            rec.care_count = len(rec.care_ids)
            rec.boarding_count = len(rec.boarding_ids)
            rec.care_cost_total = sum(rec.care_ids.mapped('cost'))

    def action_view_care(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': 'Soins',
            'res_model': 'amarna.club.horse.care', 'view_mode': 'list,form',
            'domain': [('horse_id', '=', self.id)],
            'context': {'default_horse_id': self.id}}

    def action_view_boarding(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': 'Pensions',
            'res_model': 'amarna.club.horse.boarding', 'view_mode': 'list,form',
            'domain': [('horse_id', '=', self.id)],
            'context': {'default_horse_id': self.id, 'default_owner_id': self.owner_id.id}}

    @api.constrains('box_id')
    def _check_box_capacity(self):
        self.mapped('box_id')._check_not_overbooked()

    @api.constrains('fatigue')
    def _check_fatigue(self):
        for rec in self:
            if not 0.0 <= rec.fatigue <= 1.0:
                raise ValidationError(
                    'La fatigue de « %s » doit être comprise entre 0 et 1.' % rec.name)

    @api.depends('fatigue')
    def _compute_fatigue_pct(self):
        for rec in self:
            rec.fatigue_pct = rec.fatigue * 100.0

    def _search_care_due(self, field_name, days, operator, value):
        if operator not in ('=', '!=', 'in', 'not in'):
            return NotImplemented
        # Odoo 20 turns ('x', '=', True) into ('x', 'in', OrderedSet([True])).
        values = {value} if isinstance(value, bool) else set(value)
        cutoff = fields.Date.context_today(self) - timedelta(days=days)
        want_due = (True in values) == (operator in ('=', 'in'))
        if want_due:
            return [(field_name, '!=', False), (field_name, '<', cutoff)]
        return ['|', (field_name, '=', False), (field_name, '>=', cutoff)]

    def _search_farrier_due(self, operator, value):
        days = self.env.company.amarna_farrier_interval_days
        return self._search_care_due('last_farrier', days, operator, value)

    def _search_deworming_due(self, operator, value):
        days = self.env.company.amarna_deworming_interval_days
        return self._search_care_due('last_deworming', days, operator, value)

    @api.depends('last_farrier', 'last_deworming')
    def _compute_care_due(self):
        # Intervals come from the club settings; the app reads the same values.
        company = self.env.company
        today = fields.Date.context_today(self)
        for rec in self:
            rec.farrier_due = bool(
                rec.last_farrier
                and today - rec.last_farrier > timedelta(days=company.amarna_farrier_interval_days)
            )
            rec.deworming_due = bool(
                rec.last_deworming
                and today - rec.last_deworming > timedelta(days=company.amarna_deworming_interval_days)
            )
