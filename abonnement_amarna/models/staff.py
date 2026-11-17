# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AmarnaClubStaff(models.Model):
    """Staff who can be assigned to an intervention or a task in the app.

    The tablet reads this list instead of keeping its own names.
    """
    _name = 'amarna.club.staff'
    _description = 'Personnel du club'
    _order = 'role, name'

    name = fields.Char(string='Nom', required=True)
    role = fields.Selection([
        ('technician', 'Technicien'),
        ('horse_keeper', 'Soigneur / écurie'),
        ('lifeguard', 'Maître-nageur'),
        ('instructor', 'Moniteur'),
        ('supervisor', 'Responsable'),
        ('other', 'Autre'),
    ], string='Fonction', required=True, default='technician')
    phone = fields.Char(string='Téléphone')
    user_id = fields.Many2one(
        'res.users', string='Compte Odoo', ondelete='set null',
        help="Compte avec lequel cette personne se connecte à la tablette. "
             "Son profil et ses activités y sont affichés.")
    activity_ids = fields.Many2many(
        'amarna.club.activity', 'amarna_staff_activity_rel', 'staff_id', 'activity_id',
        string='Activités affectées')
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company, required=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('user_uniq', 'unique(user_id)',
         'Un compte Odoo ne peut être lié qu\'à une seule fiche du personnel.'),
    ]

    @api.model
    def amarna_my_profile(self):
        """Staff card of the signed-in user, for the tablet profile screen."""
        staff = self.sudo().search([('user_id', '=', self.env.user.id)], limit=1)
        if not staff:
            return {}
        return {
            'name': staff.name,
            'role': dict(staff._fields['role'].selection).get(staff.role, ''),
            'phone': staff.phone or '',
            'activities': [
                {'code': act.code, 'name': act.name}
                for act in staff.activity_ids.sorted('sequence')
            ],
        }
