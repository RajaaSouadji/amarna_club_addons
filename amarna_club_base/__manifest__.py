# -*- coding: utf-8 -*-
{
    'name': 'Amarna Club - Base',
    'version': '17.0.1.0.0',
    'category': 'Services/Club',
    'summary': 'Socle commun du club : activités, groupes de sécurité',
    'author': 'Amarna',
    'license': 'LGPL-3',
    'depends': ['base', 'mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/activity_data.xml',
        'views/club_activity_views.xml',
        'views/menu_views.xml',
    ],
    'application': True,
    'installable': True,
}
