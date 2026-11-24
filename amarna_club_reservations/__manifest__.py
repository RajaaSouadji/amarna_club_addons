# -*- coding: utf-8 -*-
{
    'name': 'Amarna Club - Réservations',
    'version': '20.0.1.0.0',
    'category': 'Services/Club',
    'summary': 'Réservations des activités du club, facturation et check-in depuis la tablette',
    'author': 'Amarna',
    'license': 'LGPL-3',
    'depends': ['abonnement_amarna'],
    'data': [
        'security/ir.access.csv',
        'views/club_reservation_views.xml',
        'views/reservation_extra_views.xml',
    ],
    'application': True,
    'installable': True,
}
