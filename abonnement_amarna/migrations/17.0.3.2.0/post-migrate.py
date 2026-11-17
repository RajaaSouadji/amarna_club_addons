# -*- coding: utf-8 -*-
"""Give existing activities their dedicated tablet screen.

Before 17.0.3.2.0 the tablet chose the screen from the activity code in its
own code. The screen is now a field of the activity, editable by the admin.
Set it for the activities that already existed so the tablet keeps working.
"""
from odoo import SUPERUSER_ID, api

SCREEN_BY_CODE = {
    'pool': ('pool', "Relevés de qualité de l'eau"),
    'horses': ('horses', 'Écurie : chevaux et soins'),
    'shooting': ('armory', 'Armurerie et nettoyage'),
    'padel': ('padel', 'Terrains et réservations'),
    'paintball': ('paintball', 'Terrain et sessions'),
    'gym': ('gym', 'Machines de la salle'),
}


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for activity in env['amarna.club.activity'].with_context(active_test=False).search(
            [('mobile_screen', '=', False)]):
        screen = SCREEN_BY_CODE.get(activity.code)
        if screen:
            activity.write({'mobile_screen': screen[0], 'mobile_screen_label': screen[1]})
