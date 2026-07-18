# -*- coding: utf-8 -*-
{
    'name': 'Amarna Club - Lien Abonnements',
    'version': '17.0.1.0.0',
    'category': 'Services/Club',
    'summary': "Relie les activités opérationnelles du club aux activités "
               "du module Abonnement",
    'author': 'Amarna',
    'license': 'LGPL-3',
    'depends': ['amarna_club_base', 'Abonnement'],
    'data': [
        'views/club_activity_views.xml',
    ],
    'auto_install': True,
    'installable': True,
}
