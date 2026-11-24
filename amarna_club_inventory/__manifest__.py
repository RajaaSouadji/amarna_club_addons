# -*- coding: utf-8 -*-
{
    'name': 'Amarna Club - Inventaire',
    'version': '20.0.1.0.0',
    'category': 'Services/Club',
    'summary': 'Consommables des activités du club avec alertes de seuil',
    'author': 'Amarna',
    'license': 'LGPL-3',
    'depends': ['abonnement_amarna', 'mail'],
    'data': [
        'security/ir.access.csv',
        'data/sequence.xml',
        'views/club_inventory_views.xml',
    ],
    'demo': ['demo/inventory_demo.xml'],
    'application': True,
    'installable': True,
}
