# -*- coding: utf-8 -*-
{
    'name': 'Amarna Club - Piscine',
    'version': '17.0.1.1.0',
    'category': 'Services/Club',
    'summary': "Relevés qualité de l'eau de la piscine avec conformité",
    'author': 'Amarna',
    'license': 'LGPL-3',
    'depends': ['abonnement_amarna'],
    'data': [
        'security/ir.model.access.csv',
        'views/club_pool_reading_views.xml',
        'views/pool_settings_views.xml',
    ],
    'demo': ['demo/pool_demo.xml'],
    'application': True,
    'installable': True,
}
