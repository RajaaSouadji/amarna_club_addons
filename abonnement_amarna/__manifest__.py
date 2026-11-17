# -*- coding: utf-8 -*-
{
    'name': 'Amarna Club - Abonnements, facturation & accès RFID',
    'version': '17.0.3.2.0',
    'category': 'Services',
    'summary': 'Socle du club : formules, facturation centralisée, encaissements et accès RFID',
    'description': """
Socle partagé par tout le club.

* Abonnements (formules, durées calendaires, séances, renouvellement).
* Facturation unique : chaque montant dû ou payé provient d'une facture
  comptable Odoo ; les réservations utilisent le même mécanisme.
* Accès RFID déduit de l'état de paiement de la période en cours.
    """,
    'author': 'Amarna',
    'license': 'LGPL-3',
    'depends': ['base', 'account', 'mail', 'product'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/activity_data.xml',
        'data/subscription_sequence.xml',
        'data/rfid_cron.xml',
        'views/menu_views.xml',
        'views/res_config_settings_views.xml',
        'views/staff_views.xml',
        'views/activity_views.xml',
        'views/subscription_type_views.xml',
        'views/subscription_plan_views.xml',
        'views/subscription_views.xml',
        'views/billing_views.xml',
        'views/rfid_views.xml',
        'views/rfid_access_views.xml',
        'views/scan_wizard_views.xml',
        'views/checkin_views.xml',
    ],
    'demo': ['demo/activity_demo.xml'],
    'application': True,
    'installable': True,
}
