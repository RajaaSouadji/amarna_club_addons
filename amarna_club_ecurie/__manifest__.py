# -*- coding: utf-8 -*-
{
    'name': 'Amarna Club - Écurie',
    'version': '17.0.1.2.0',
    'category': 'Services/Club',
    'summary': 'Gestion des chevaux : statut, fatigue, soins vétérinaires',
    'author': 'Amarna',
    'license': 'LGPL-3',
    'depends': ['abonnement_amarna'],
    'data': [
        'security/ir.model.access.csv',
        'views/club_horse_views.xml',
        'views/horse_settings_views.xml',
    ],
    'demo': ['demo/horse_demo.xml'],
    'application': True,
    'installable': True,
}
