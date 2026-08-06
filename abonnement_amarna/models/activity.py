# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AmarnaClubActivity(models.Model):
    _name = 'amarna.club.activity'
    _description = 'Activité du club'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    icon_key = fields.Char(string='Icône mobile')
    mobile_status = fields.Selection([
        ('open', 'Ouvert'),
        ('closed', 'Fermé'),
        ('warning', 'Attention'),
        ('maintenance', 'En maintenance'),
    ], string='Statut opérationnel', default='open')
    closure_start = fields.Datetime(string='Fermeture du')
    closure_end = fields.Datetime(string='Fermeture au')
    current_occupancy = fields.Integer(string='Occupation actuelle')
    max_capacity = fields.Integer(string='Capacité maximale')
    assigned_staff = fields.Char(string='Personnel en service')
    occupancy_pct = fields.Float(
        string="Taux d'occupation (%)",
        compute='_compute_occupancy_pct',
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Couleur')

    subscription_plan_ids = fields.One2many(
        "amarna.subscription.plan",
        "activity_id",
        string="Plans d'abonnement",
    )
    subscription_plan_count = fields.Integer(
        compute="_compute_subscription_plan_count"
    )

    description = fields.Html()
    image_1920 = fields.Image("Image", max_width=1920, max_height=1920)
    note = fields.Html(string="Notes internes")

    _sql_constraints = [
        ('code_uniq', 'unique(code)', "Le code d'activité doit être unique."),
    ]

    @api.model
    def _prepare_default_activity_xmlids(self):
        """Attach default activity XML IDs to pre-existing rows.

        Older or partially completed installations can contain the seed rows
        but not their ``ir.model.data`` entries. Loading the XML again would
        then attempt to create a second row and violate ``code_uniq``.
        """
        defaults = {
            'pool': 'activity_pool',
            'horses': 'activity_horses',
            'shooting': 'activity_shooting',
            'paintball': 'activity_paintball',
            'gym': 'activity_gym',
            'padel': 'activity_padel',
        }
        model_data = self.env['ir.model.data'].sudo()
        for code, xml_name in defaults.items():
            if model_data.search([
                ('module', '=', 'abonnement_amarna'),
                ('name', '=', xml_name),
            ], limit=1):
                continue
            activity = self.search([('code', '=', code)], limit=1)
            if activity:
                model_data.create({
                    'module': 'abonnement_amarna',
                    'name': xml_name,
                    'model': self._name,
                    'res_id': activity.id,
                    'noupdate': True,
                })
    @api.constrains('closure_start', 'closure_end')
    def _check_closure_period(self):
        for activity in self:
            if activity.closure_start and activity.closure_end and activity.closure_end <= activity.closure_start:
                raise ValidationError(
                    'La fin de fermeture doit être postérieure au début de fermeture.'
                )

    @api.depends('current_occupancy', 'max_capacity')
    def _compute_occupancy_pct(self):
        for rec in self:
            rec.occupancy_pct = (
                rec.current_occupancy * 100.0 / rec.max_capacity
                if rec.max_capacity else 0.0
            )

    @api.depends("subscription_plan_ids")
    def _compute_subscription_plan_count(self):
        for rec in self:
            rec.subscription_plan_count = len(rec.subscription_plan_ids)

    @api.model
    def _find_by_mobile_code(self, code):
        if not code:
            return self.browse()
        return self.search(
            ['|', ('code', '=ilike', code), ('name', '=ilike', code)],
            limit=1,
        )

    def action_view_subscription_plans(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Plans",
            "res_model": "amarna.subscription.plan",
            "view_mode": "tree,form",
            "domain": [("activity_id", "=", self.id)],
            "context": {
                "default_activity_id": self.id,
            },
        }