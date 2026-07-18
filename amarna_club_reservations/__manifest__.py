# -*- coding: utf-8 -*-
{
    'name': 'Amarna Club - Réservations',
    'version': '17.0.1.0.0',
    'category': 'Services/Club',
    'summary': 'Réservations des activités du club avec check-in tablette',
    'author': 'Amarna',
    'license': 'LGPL-3',
    'depends': ['amarna_club_base'],
    'data': [
        'security/ir.model.access.csv',
        'views/club_reservation_views.xml',
    ],
    'application': True,
    'installable': True,
}
