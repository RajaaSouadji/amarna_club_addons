# -*- coding: utf-8 -*-
{
    'name': 'Amarna Club - Équipements',
    'version': '17.0.1.0.0',
    'category': 'Services/Club',
    'summary': 'Équipements et infrastructures du club (armurerie incluse)',
    'author': 'Amarna',
    'license': 'LGPL-3',
    'depends': ['amarna_club_base'],
    'data': [
        'security/ir.model.access.csv',
        'data/asset_data.xml',
        'views/club_asset_views.xml',
    ],
    'application': True,
    'installable': True,
}
