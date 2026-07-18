# -*- coding: utf-8 -*-
{
    'name': 'Amarna Club - Interventions',
    'version': '17.0.1.0.0',
    'category': 'Services/Club',
    'summary': 'Incidents et maintenance du club (flux unifié tablette)',
    'author': 'Amarna',
    'license': 'LGPL-3',
    'depends': ['amarna_club_base', 'amarna_club_assets'],
    'data': [
        'security/ir.model.access.csv',
        'views/club_intervention_views.xml',
    ],
    'application': True,
    'installable': True,
}
