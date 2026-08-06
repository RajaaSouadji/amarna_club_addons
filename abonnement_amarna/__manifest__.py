# -*- coding: utf-8 -*-
{
    'name': 'Amarna Club - Abonnements, Réservations & RFID',
    'version': '17.0.2.0',
    'category': 'Services',
    'summary': 'Gestion unifiée des abonnements, réservations, paiements et accès RFID',
    'author': 'Amarna',
    'license': 'LGPL-3',
    'depends': ['base', 'account', 'mail', 'product', 'amarna_club_base'],
    'data': [
        'security/ir.model.access.csv',
        'data/subscription_sequence.xml',
        'data/rfid_cron.xml',
        'views/menu_views.xml',
        'views/activity_views.xml',
        'views/subscription_plan_views.xml',
        'views/subscription_type_views.xml',
        'views/subscription_views.xml',
        # 'views/amarna_duration_unit.xml',
        # 'views/recurring_plan_views.xml',
        'views/recurring_plan_line_views.xml',
        'views/amarna_subscription_line_views.xml',
        'views/rfid_views.xml',
        'views/rfid_access_views.xml',
        'views/payment_views.xml',
        # 'views/history_views.xml',
        'views/reservation_views.xml',
        # 'views/report_views.xml',
        'views/scan_wizard_views.xml',
        'views/checkin_views.xml',

    ],
    'application': True,
    'installable': True,
}




