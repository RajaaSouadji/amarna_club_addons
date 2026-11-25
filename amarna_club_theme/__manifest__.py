# -*- coding: utf-8 -*-
{
    'name': 'Amarna Club - Navigation',
    'version': '20.0.1.0.0',
    'category': 'Services/Club',
    'summary': "Barre latérale des applications avec icônes (remplace la liste déroulante)",
    'author': 'Amarna',
    'license': 'LGPL-3',
    'depends': ['web'],
    'assets': {
        'web.assets_backend': [
            'amarna_club_theme/static/src/app_sidebar/*',
        ],
    },
    'installable': True,
    'auto_install': False,
}
