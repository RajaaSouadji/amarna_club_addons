# -*- coding: utf-8 -*-
{
    'name': 'Amarna Club - SMS de fin d\'abonnement',
    'version': '20.0.1.0.0',
    'category': 'Services/Club',
    'summary': "SMS automatique au membre quelques jours avant la fin de son abonnement",
    'description': """
Un SMS part, chaque matin, vers les membres dont l'abonnement se termine dans
N jours (2 par défaut). **Désactivé par défaut** : il faut l'activer dans
Paramètres > Club Amarna.

Les SMS passent par le module « SMS » d'Odoo : ils partent par le service
d'Odoo (IAP) et consomment des crédits SMS. Un autre fournisseur se branche
en remplaçant l'envoi de ``sms.sms``.
    """,
    'author': 'Amarna',
    'license': 'LGPL-3',
    'depends': ['abonnement_amarna', 'sms'],
    'data': [
        'data/sms_cron.xml',
        'views/res_config_settings_views.xml',
        'views/subscription_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
