from odoo import api, fields, models


class AmarnaCheckin(models.Model):
    _name = 'amarna.checkin'
    _description = 'Contrôle d’accès RFID'
    _order = 'checkin_datetime desc, id desc'

    name = fields.Char(string='Référence', required=True, default='Nouveau', copy=False)
    partner_id = fields.Many2one('res.partner', string='Membre', required=True, ondelete='restrict')
    card_id = fields.Many2one('amarna.rfid.card', string='Carte RFID', required=True, ondelete='restrict')
    subscription_id = fields.Many2one('amarna.subscription', string='Abonnement', required=True, ondelete='restrict')
    checkin_datetime = fields.Datetime(string='Date et heure', required=True, default=fields.Datetime.now)
    checkin_date = fields.Date(string='Date', compute='_compute_checkin_parts', store=True)
    checkin_time = fields.Char(string='Heure', compute='_compute_checkin_time', store=True)
    sessions_before = fields.Integer(string='Séances avant', required=True)
    sessions_after = fields.Integer(string='Séances après', required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)

    @api.depends('checkin_datetime')
    def _compute_checkin_parts(self):
        for record in self:
            if record.checkin_datetime:
                local_dt = fields.Datetime.context_timestamp(record, record.checkin_datetime)
                record.checkin_date = local_dt.date()
                record.checkin_time = local_dt.strftime('%H:%M:%S')
            else:
                record.checkin_date = False
                record.checkin_time = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') in ('New', 'Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('amarna.checkin') or 'Nouveau'
        return super().create(vals_list)
