# -*- coding: utf-8 -*-
{
    'name': 'Amarna Club - Écurie',
    'version': '17.0.1.0.0',
    'category': 'Services/Club',
    'summary': 'Gestion des chevaux : statut, fatigue, soins vétérinaires',
    'author': 'Amarna',
    'license': 'LGPL-3',
    'depends': ['amarna_club_base'],
    'data': [
        'security/ir.model.access.csv',
        'data/horse_data.xml',
        'views/club_horse_views.xml',
    ],
    'application': True,
    'installable': True,
}
