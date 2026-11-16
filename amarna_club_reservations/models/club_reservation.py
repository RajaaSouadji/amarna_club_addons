# -*- coding: utf-8 -*-
"""Compatibility extension for the standalone reservations addon.

The reservation model is owned by ``abonnement_amarna``.  Keeping a second
``_name = 'amarna.club.reservation'`` definition here used to replace fields
and business rules depending on module load order.  This addon intentionally
extends the canonical model instead.
"""
from odoo import models


class AmarnaClubReservation(models.Model):
    _inherit = 'amarna.club.reservation'
