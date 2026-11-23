# -*- coding: utf-8 -*-
{
    'name': 'Amarna Club - Équipements',
    'version': '20.0.1.0.0',
    'category': 'Services/Club',
    'summary': 'Équipements et infrastructures du club (armurerie incluse)',
    'author': 'Amarna',
    'license': 'LGPL-3',
    'depends': ['abonnement_amarna'],
    'data': [
        'security/ir.access.csv',
        'views/club_asset_views.xml',
        'views/checkpoint_views.xml',
        'views/assets_settings_views.xml',
    ],
    'demo': ['demo/asset_demo.xml'],
    'application': True,
    'installable': True,
}
