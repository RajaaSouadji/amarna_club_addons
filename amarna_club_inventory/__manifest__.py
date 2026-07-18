# -*- coding: utf-8 -*-
{
    'name': 'Amarna Club - Inventaire',
    'version': '17.0.1.0.0',
    'category': 'Services/Club',
    'summary': 'Consommables des activités du club avec alertes de seuil',
    'author': 'Amarna',
    'license': 'LGPL-3',
    'depends': ['amarna_club_base'],
    'data': [
        'security/ir.model.access.csv',
        'data/inventory_data.xml',
        'views/club_inventory_views.xml',
    ],
    'application': True,
    'installable': True,
}
