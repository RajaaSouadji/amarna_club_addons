# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class AmarnaClubWeaponLog(models.Model):
    """Armoury register: who took which weapon out, and when it came back."""
    _name = 'amarna.club.weapon.log'
    _inherit = ['mail.thread']
    _description = "Registre de l'armurerie"
    _order = 'issued_at desc, id desc'

    asset_id = fields.Many2one(
        'amarna.club.asset', string='Arme', required=True, index=True,
        domain=[('is_weapon', '=', True)], tracking=True)
    partner_id = fields.Many2one('res.partner', string='Membre', tracking=True)
    issued_by_id = fields.Many2one('amarna.club.staff', string='Remise par')
    issued_at = fields.Datetime(
        string='Remise le', required=True, default=fields.Datetime.now)
    returned_at = fields.Datetime(string='Rendue le', readonly=True, copy=False)
    ammo_issued = fields.Integer(string='Munitions remises')
    ammo_returned = fields.Integer(string='Munitions rendues')
    state = fields.Selection(
        [('issued', 'Remise'), ('returned', 'Rendue')],
        string='État', default='issued', required=True, tracking=True, copy=False)
    notes = fields.Text(string='Notes')

    @api.model_create_multi
    def create(self, vals_list):
        logs = super().create(vals_list)
        for log in logs:
            if log.state == 'issued':
                self._check_not_already_issued(log)
                log.asset_id.write({'status': 'inUse'})
        return logs

    @api.model
    def _check_not_already_issued(self, log):
        other = self.search([
            ('asset_id', '=', log.asset_id.id), ('state', '=', 'issued'),
            ('id', '!=', log.id)], limit=1)
        if other:
            raise UserError(
                "L'arme « %s » est déjà remise à %s." % (
                    log.asset_id.name, other.partner_id.name or 'un membre'))

    def action_return(self):
        for log in self.filtered(lambda r: r.state == 'issued'):
            log.write({'state': 'returned', 'returned_at': fields.Datetime.now()})
            log.asset_id.write({'status': 'available'})

    @api.depends('asset_id', 'partner_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s – %s' % (
                rec.asset_id.name or 'Arme', rec.partner_id.name or '')
