# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AmarnaClubAsset(models.Model):
    _name = 'amarna.club.asset'
    _description = 'Équipement du club'
    _order = 'activity_id, name'

    name = fields.Char(required=True)

    code = fields.Char(
        string='Code mobile',
        index=True,
        copy=False,
        help="Identifiant de l'asset dans l'application tablette "
             "(ex: asset-pool-filter-01).",
    )

    serial_number = fields.Char(string='Numéro de série')

    category = fields.Char(
        string='Catégorie',
        help="Libellé affiché dans l'application "
             "(ex: Équipement Piscine, Arme de Poing).",
    )

    mobile_activity_code = fields.Char(
        string='Code activité mobile',
        help="Code d'activité envoyé par la tablette; le lien Activité "
             "est résolu automatiquement.",
    )

    activity_id = fields.Many2one(
        'amarna.club.activity',
        string='Activité',
        compute='_compute_activity_id',
        store=True,
        readonly=False,
    )

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
        compute='_compute_is_weapon',
        store=True,
    )

    active = fields.Boolean(default=True)

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

    @api.depends('category')
    def _compute_is_weapon(self):
        for rec in self:
            rec.is_weapon = 'arme' in (rec.category or '').lower()
