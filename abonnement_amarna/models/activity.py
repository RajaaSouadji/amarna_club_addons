# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError

# Statuses that accept reservations. "warning" (Attention) means the activity
# runs but needs a look (e.g. a horse is injured): bookings stay allowed.
BOOKABLE_STATUSES = ('open', 'warning')
# Statuses that start an automatic closure period when they are set.
AUTO_CLOSURE_STATUSES = ('closed', 'maintenance')


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
    closure_duration_hours = fields.Float(
        string='Durée de fermeture (h)',
        compute='_compute_closure_duration',
        help='Durée calculée à partir des dates de fermeture optionnelles.',
    )
    current_occupancy = fields.Integer(string='Occupation actuelle')
    max_capacity = fields.Integer(string='Capacité maximale')
    assigned_staff = fields.Char(string='Personnel en service')
    unit_price = fields.Float(
        string='Tarif par personne (HT)', default=0.0,
        help="Tarif d'une réservation par personne, hors taxes. 0 = gratuit.")
    billing_product_id = fields.Many2one(
        'product.product', string='Produit de facturation', copy=False,
        help="Produit de service utilisé pour facturer les réservations. "
             "Créé automatiquement si vide.")
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

    def _get_billing_product(self):
        """Service product that carries this activity's reservation revenue."""
        self.ensure_one()
        if not self.billing_product_id:
            self.billing_product_id = self.env['product.product']._amarna_service(
                'AMARNA-ACT-%s' % self.code, 'Réservation – %s' % self.name)
        return self.billing_product_id

    @api.constrains('closure_start', 'closure_end')
    def _check_closure_period(self):
        for activity in self:
            if (activity.closure_start and activity.closure_end
                    and activity.closure_end <= activity.closure_start):
                raise ValidationError(
                    'La fin de fermeture doit être postérieure au début de fermeture.'
                )

    @api.depends('closure_start', 'closure_end')
    def _compute_closure_duration(self):
        for activity in self:
            if activity.closure_start and activity.closure_end:
                delta = activity.closure_end - activity.closure_start
                activity.closure_duration_hours = delta.total_seconds() / 3600.0
            else:
                activity.closure_duration_hours = 0.0

    @api.onchange('mobile_status')
    def _onchange_mobile_status(self):
        """Start a closure period when an activity is taken offline.

        The end stays optional: empty means an indefinite closure, a value is
        the planned reopening. Reopening closes the running period.
        """
        now = fields.Datetime.now()
        for activity in self:
            origin = activity._origin
            if not origin or not origin.id:
                continue
            for field_name, value in origin._closure_change_vals(activity.mobile_status, now).items():
                activity[field_name] = value

    def _closure_change_vals(self, status, now):
        """Closure dates to write when one activity changes to ``status``.

        Only real status transitions touch the closure window:
        - entering a closed/maintenance state opens a new window from now;
        - leaving it ends the running window (or drops it when it lasted
          less than a second, which would otherwise break the end > start rule).
        """
        self.ensure_one()
        if status == self.mobile_status:
            return {}
        running = bool(
            self.closure_start and self.closure_start <= now
            and (not self.closure_end or self.closure_end > now)
        )
        if status in AUTO_CLOSURE_STATUSES:
            if running:
                return {}
            return {'closure_start': now, 'closure_end': False}
        if status in BOOKABLE_STATUSES and self.mobile_status in AUTO_CLOSURE_STATUSES and running:
            if self.closure_start < now:
                return {'closure_end': now}
            return {'closure_start': False, 'closure_end': False}
        return {}

    def write(self, vals):
        """Keep the closure window in sync with status changes.

        JSON-RPC writes (tablet, API) do not run form onchanges, so the
        window is maintained here. Explicit closure dates are never overridden.
        """
        vals = dict(vals)
        status = vals.get('mobile_status')
        if status and 'closure_start' not in vals and 'closure_end' not in vals:
            if len(self) > 1:
                result = True
                for rec in self:
                    result = rec.write(dict(vals)) and result
                return result
            if self:
                vals.update(self._closure_change_vals(status, fields.Datetime.now()))
        return super().write(vals)

    def is_available_at(self, start_at, end_at):
        """Return whether the activity can host the complete time slot.

        Datetimes are naive UTC, as stored by Odoo. Intervals are half-open:
        a booking that ends exactly when a closure starts is valid.
        """
        self.ensure_one()
        start_at = fields.Datetime.to_datetime(start_at)
        end_at = fields.Datetime.to_datetime(end_at)
        if not start_at or not end_at or start_at >= end_at:
            return False
        if self.mobile_status not in BOOKABLE_STATUSES:
            return False
        if self.closure_start:
            if not self.closure_end:
                return end_at <= self.closure_start
            if start_at < self.closure_end and end_at > self.closure_start:
                return False
        return True

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
        """Resolve the activity code sent by the tablet (code or name)."""
        if not code:
            return self.browse()
        return self.search(
            [('code', '=', code)], limit=1
        ) or self.search([('name', '=ilike', code)], limit=1)

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
