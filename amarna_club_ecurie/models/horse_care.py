# -*- coding: utf-8 -*-
from datetime import datetime, time

from odoo import api, fields, models

CARE_TYPES = [
    ('farrier', 'Maréchal-ferrant'),
    ('vaccine', 'Vaccin'),
    ('deworming', 'Vermifuge'),
    ('dentist', 'Dentiste'),
    ('vet', 'Vétérinaire'),
    ('physio', 'Kiné / ostéopathe'),
    ('other', 'Autre'),
]


class AmarnaClubHorseCare(models.Model):
    """Health journal of a horse: each visit or treatment, with its cost."""
    _name = 'amarna.club.horse.care'
    _description = "Soin d'un cheval"
    _order = 'date desc, id desc'

    horse_id = fields.Many2one(
        'amarna.club.horse', string='Cheval', required=True, ondelete='cascade', index=True)
    care_type = fields.Selection(CARE_TYPES, string='Soin', required=True, default='vet')
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    next_due = fields.Date(
        string='Prochain soin', help="Pour une visite vétérinaire, met à jour la prochaine visite du cheval.")
    provider_id = fields.Many2one('res.partner', string='Intervenant')
    description = fields.Char(string='Détail')
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)
    cost = fields.Monetary(string='Coût', currency_field='currency_id')
    notes = fields.Text(string='Notes')

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_next_visit()
        return records

    def write(self, vals):
        result = super().write(vals)
        if 'next_due' in vals or 'care_type' in vals:
            self._sync_next_visit()
        return result

    def _sync_next_visit(self):
        for care in self.filtered(lambda c: c.care_type == 'vet' and c.next_due):
            care.horse_id.next_vet_visit = datetime.combine(care.next_due, time(9, 0))

    @api.depends('horse_id', 'care_type', 'date')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s – %s' % (
                rec.horse_id.name or 'Soin',
                dict(rec._fields['care_type']._description_selection(rec.env)).get(rec.care_type, ''))


class AmarnaClubHorseFeed(models.Model):
    """One line of a horse's feeding plan."""
    _name = 'amarna.club.horse.feed'
    _description = "Ration d'un cheval"
    _order = 'horse_id, sequence, id'

    horse_id = fields.Many2one(
        'amarna.club.horse', string='Cheval', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    meal = fields.Selection(
        [('morning', 'Matin'), ('noon', 'Midi'), ('evening', 'Soir')],
        string='Repas', required=True, default='morning')
    feed_name = fields.Char(string='Aliment', required=True)
    quantity = fields.Float(string='Quantité', default=1.0)
    unit = fields.Char(string='Unité', default='kg')
    notes = fields.Char(string='Remarque')

    @api.depends('horse_id', 'feed_name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s – %s' % (rec.horse_id.name or 'Ration', rec.feed_name or '')
