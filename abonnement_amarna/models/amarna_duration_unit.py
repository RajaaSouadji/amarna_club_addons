from odoo import models, fields, api



class AmarnaDurationUnit(models.Model):
    _name = 'amarna.duration.unit'
    _description = 'Duration Unit'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    active = fields.Boolean(default=True)