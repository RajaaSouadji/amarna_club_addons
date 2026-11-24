# -*- coding: utf-8 -*-
{
    'name': 'Amarna Club - Personnel',
    'version': '20.0.1.0.0',
    'category': 'Services/Club',
    'summary': 'Équipe du club : certifications avec échéance, planning des gardes',
    'author': 'Amarna',
    'license': 'LGPL-3',
    'depends': ['abonnement_amarna', 'mail'],
    'data': [
        'security/ir.access.csv',
        'views/staff_extra_views.xml',
    ],
    'application': True,
    'installable': True,
}
