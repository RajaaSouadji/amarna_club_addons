# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models


class AmarnaClubPoolTask(models.Model):
    """Recurring chore of the pool (backwash, filter cleaning, dosing pump...).

    Like a preventive plan of Odoo Maintenance: each task has an interval, the
    date it was last done and the date it is next due."""
    _name = 'amarna.club.pool.task'
    _inherit = ['mail.thread']
    _description = "Tâche d'entretien de la piscine"
    _order = 'next_due, name'

    name = fields.Char(string='Tâche', required=True, tracking=True)
    interval_days = fields.Integer(
        string='Tous les (jours)', default=7, required=True,
        help="Fréquence de la tâche. La prochaine échéance se calcule à partir de la dernière exécution.")
    last_done = fields.Date(string='Dernière exécution', readonly=True, copy=False)
    next_due = fields.Date(
        string='Prochaine échéance', compute='_compute_next_due', store=True, readonly=False)
    staff_id = fields.Many2one('amarna.club.staff', string='Responsable')
    state = fields.Selection(
        [('ok', 'À jour'), ('soon', 'Bientôt'), ('late', 'En retard')],
        string='État', compute='_compute_state', search='_search_state')
    instructions = fields.Html(string='Mode opératoire')
    log_ids = fields.One2many('amarna.club.pool.task.log', 'task_id', string='Historique')
    active = fields.Boolean(default=True)

    @api.depends('last_done', 'interval_days')
    def _compute_next_due(self):
        today = fields.Date.context_today(self)
        for rec in self:
            base = rec.last_done or today
            rec.next_due = base + timedelta(days=rec.interval_days)

    @api.depends('next_due')
    def _compute_state(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if not rec.next_due or rec.next_due > today + timedelta(days=2):
                rec.state = 'ok'
            elif rec.next_due >= today:
                rec.state = 'soon'
            else:
                rec.state = 'late'

    def _search_state(self, operator, value):
        if operator not in ('=', 'in'):
            return NotImplemented
        values = {value} if isinstance(value, str) else set(value)
        today = fields.Date.context_today(self)
        soon = today + timedelta(days=2)
        parts = []
        if 'late' in values:
            parts.append([('next_due', '<', today)])
        if 'soon' in values:
            parts.append([('next_due', '>=', today), ('next_due', '<=', soon)])
        if 'ok' in values:
            parts.append([('next_due', '>', soon)])
        if not parts:
            return [('id', '=', False)]
        domain = parts[0]
        for extra in parts[1:]:
            domain = ['|'] + domain + extra
        return domain

    def action_done(self):
        """Mark the task as done today and log who did it."""
        today = fields.Date.context_today(self)
        for rec in self:
            self.env['amarna.club.pool.task.log'].create({
                'task_id': rec.id, 'date': today, 'user_id': self.env.user.id})
            rec.write({'last_done': today})
            rec.next_due = today + timedelta(days=rec.interval_days)


class AmarnaClubPoolTaskLog(models.Model):
    _name = 'amarna.club.pool.task.log'
    _description = "Exécution d'une tâche d'entretien de la piscine"
    _order = 'date desc, id desc'

    task_id = fields.Many2one(
        'amarna.club.pool.task', string='Tâche', required=True, ondelete='cascade', index=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    user_id = fields.Many2one('res.users', string='Réalisé par', default=lambda self: self.env.user)
    notes = fields.Char(string='Remarque')
