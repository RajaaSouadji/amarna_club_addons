# -*- coding: utf-8 -*-
{
    'name': 'Amarna Club - Pièces utilisées en maintenance',
    'version': '20.0.1.0.0',
    'category': 'Services/Club',
    'summary': "Lie la maintenance au stock : les pièces d'un ticket sortent du stock à la clôture",
    'author': 'Amarna',
    'license': 'LGPL-3',
    'depends': ['amarna_club_interventions', 'amarna_club_inventory'],
    'data': [
        'security/ir.access.csv',
        'views/intervention_part_views.xml',
    ],
    'auto_install': True,
    'installable': True,
}
