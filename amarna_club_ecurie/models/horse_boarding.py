# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class AmarnaClubHorseBoarding(models.Model):
    """Boarding contract: an owner keeps a horse at the stable for a monthly fee."""
    _name = 'amarna.club.horse.boarding'
    _inherit = ['mail.thread']
    _description = "Contrat de pension"
    _order = 'date_start desc, id desc'

    name = fields.Char(string='Référence', compute='_compute_name', store=True)
    horse_id = fields.Many2one(
        'amarna.club.horse', string='Cheval', required=True, tracking=True)
    owner_id = fields.Many2one('res.partner', string='Propriétaire', required=True, tracking=True)
    box_id = fields.Many2one('amarna.club.horse.box', string='Box / paddock')
    date_start = fields.Date(string='Début', required=True, default=fields.Date.context_today)
    date_end = fields.Date(string='Fin', help="Vide : contrat à durée indéterminée.")
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)
    monthly_fee = fields.Monetary(string='Tarif mensuel', currency_field='currency_id', required=True)
    state = fields.Selection(
        [('draft', 'Brouillon'), ('running', 'En cours'), ('ended', 'Terminé')],
        default='draft', required=True, tracking=True, copy=False)
    invoice_ids = fields.One2many('account.move', 'amarna_boarding_id', string='Factures')
    invoice_count = fields.Integer(compute='_compute_invoice_count')
    notes = fields.Text(string='Conditions')

    @api.depends('horse_id.name', 'owner_id.name')
    def _compute_name(self):
        for rec in self:
            rec.name = 'Pension %s – %s' % (rec.horse_id.name or '', rec.owner_id.name or '')

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_end and rec.date_end < rec.date_start:
                raise ValidationError("La fin du contrat doit suivre son début.")

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = len(rec.invoice_ids)

    def action_start(self):
        for rec in self:
            rec.state = 'running'
            rec.horse_id.write({'owner_id': rec.owner_id.id, 'is_boarder': True})
            if rec.box_id:
                rec.horse_id.box_id = rec.box_id

    def action_end(self):
        for rec in self:
            rec.state = 'ended'
            if not rec.date_end:
                rec.date_end = fields.Date.context_today(self)

    def action_invoice_month(self):
        """Draft invoice for the owner: one month of boarding."""
        self.ensure_one()
        if self.state != 'running':
            raise UserError("Seul un contrat en cours peut être facturé.")
        today = fields.Date.context_today(self)
        label = 'Pension %s – %s' % (self.horse_id.name, today.strftime('%m/%Y'))
        if self.invoice_ids.filtered(lambda m: m.invoice_date and m.invoice_date.strftime('%Y%m') == today.strftime('%Y%m')
                                     and m.state != 'cancel'):
            raise UserError("Le mois %s est déjà facturé." % today.strftime('%m/%Y'))
        product = self.env['product.product']._amarna_service('AMARNA-BOARDING', 'Pension équine')
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice', 'partner_id': self.owner_id.id,
            'invoice_date': today, 'amarna_boarding_id': self.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': product.id, 'name': label, 'quantity': 1,
                'price_unit': self.monthly_fee})]})
        return {
            'type': 'ir.actions.act_window', 'res_model': 'account.move',
            'res_id': invoice.id, 'view_mode': 'form'}

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': 'Factures de pension',
            'res_model': 'account.move', 'view_mode': 'list,form',
            'domain': [('amarna_boarding_id', '=', self.id)]}


class AccountMove(models.Model):
    _inherit = 'account.move'

    amarna_boarding_id = fields.Many2one(
        'amarna.club.horse.boarding', string='Contrat de pension',
        copy=False, index=True, ondelete='set null')
