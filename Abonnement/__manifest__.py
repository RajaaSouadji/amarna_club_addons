# -*- coding: utf-8 -*-
{
    'name': 'Amarna Subscription',
    'version': '17.0.1.0',
    'category': 'Services',
    'summary': 'Amarna Activity Subscription Management',
    'author': 'Amarna',
    'depends': ['base', 'account','mail','product',],
    'data': [
        'security/ir.model.access.csv',
        'data/subscription_sequence.xml',
        'views/menu_views.xml',
        'views/activity_views.xml',
        'views/subscription_plan_views.xml',
        'views/subscription_type_views.xml',
        'views/subscription_views.xml',
        'views/amarna_duration_unit.xml',
        'views/recurring_plan_views.xml',
        'views/recurring_plan_line_views.xml',
        'views/amarna_subscription_line_views.xml',

    ],
    'application': True,
    'installable': True,
}

