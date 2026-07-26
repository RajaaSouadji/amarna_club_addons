# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class AmarnaScanWizard(models.TransientModel):
    """Wizard de scan de carte RFID simulé dans Odoo.

    L'utilisateur sélectionne une carte RFID, puis clique sur "Scanner".
    Le système vérifie si la carte et l'abonnement sont valides et affiche
    les informations. L'utilisateur clique ensuite sur "Valider le scan"
    pour décrémenter une séance et enregistrer le check-in.
    """
    _name = 'amarna.scan.wizard'
    _description = 'Scan de carte RFID - Simulation'

    card_id = fields.Many2one(
        'amarna.rfid.card',
        string='Carte RFID',
        required=True,
        help="Sélectionnez la carte RFID à scanner.",
    )

    # Informations du membre et de l'abonnement (affichées après le scan)
    partner_id = fields.Many2one('res.partner', string='Nom du client', readonly=True)
    rfid_uid = fields.Char(string='Carte RFID', readonly=True)
    activity_id = fields.Many2one('amarna.club.activity', string='Activité', readonly=True)
    subscription_type_id = fields.Many2one('amarna.subscription.type', string="Type d'abonnement", readonly=True)
    start_date = fields.Date(string='Date de début', readonly=True)
    expiration_date = fields.Date(string='Date de fin', readonly=True)
    remaining_sessions = fields.Integer(string='Nombre de séances restantes', readonly=True)
    card_state = fields.Selection([
        ('active', 'Active'), ('inactive', 'Inactive'), ('lost', 'Perdue'), ('blocked', 'Bloquée'),
    ], string='Statut de la carte', readonly=True)
    subscription_status = fields.Selection([
        ('draft', 'Brouillon'), ('running', 'En cours'), ('paid', 'Payé'), ('closed', 'Clos'), ('cancel', 'Annulé'),
    ], string="Statut de l'abonnement", readonly=True)

    result_state = fields.Selection([
        ('pending', 'En attente de scan'),
        ('ok', 'Prêt à valider'),
        ('denied', 'Accès refusé'),
        ('success', 'Accès autorisé'),
    ], default='pending', string='Résultat', readonly=True)

    result_message = fields.Text(string='Message', readonly=True)

    def action_scan(self):
        """Simule le scan de la carte sélectionnée."""
        self.ensure_one()
        if not self.card_id:
            raise UserError("Veuillez sélectionner une carte RFID.")

        # Réinitialisation des champs d'information
        self.partner_id = False
        self.rfid_uid = False
        self.activity_id = False
        self.subscription_type_id = False
        self.start_date = False
        self.expiration_date = False
        self.remaining_sessions = 0
        self.card_state = False
        self.subscription_status = False
        self.result_message = False

        # 1. Vérifier si la carte est active
        if not self.card_id.active or self.card_id.state != 'active':
            self.result_state = 'denied'
            self.result_message = "❌ Cette carte RFID est désactivée."
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'amarna.scan.wizard',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
            }

        # 2. Rechercher l'abonnement actif lié à cette carte
        sub = self.env['amarna.subscription'].search([
            ('rfid_card_id', '=', self.card_id.id),
            ('active', '=', True),
        ], limit=1)

        if not sub:
            self.result_state = 'denied'
            self.result_message = "❌ Aucun abonnement actif trouvé pour cette carte."
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'amarna.scan.wizard',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
            }

        # 3. Vérifier les conditions de l'abonnement
        # Abonnement inactif (si state n'est pas 'sale' ou si active est faux)
        if not sub.active or sub.state != 'sale':
            self.result_state = 'denied'
            self.result_message = "Abonnement inactif."
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'amarna.scan.wizard',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
            }

        # Abonnement expiré
        if sub.expiration_date and sub.expiration_date < fields.Date.today():
            self.result_state = 'denied'
            self.result_message = "Abonnement expiré."
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'amarna.scan.wizard',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
            }

        # Aucune séance restante
        if sub.remaining_sessions <= 0:
            self.result_state = 'denied'
            self.result_message = "Aucune séance restante."
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'amarna.scan.wizard',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
            }

        # 4. Si toutes les conditions sont valides, remplir les infos du membre
        self.partner_id = sub.partner_id.id
        self.rfid_uid = self.card_id.name
        self.activity_id = sub.activity_id.id if sub.activity_id else False
        self.subscription_type_id = sub.plan_id.subscription_type_id.id if sub.plan_id and sub.plan_id.subscription_type_id else False
        self.start_date = sub.start_date
        self.expiration_date = sub.expiration_date
        self.remaining_sessions = sub.remaining_sessions
        self.card_state = self.card_id.state
        self.subscription_status = sub.subscription_status
        self.result_state = 'ok'
        self.result_message = "Carte et abonnement valides. Prêt à valider le scan."

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'amarna.scan.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_do_checkin(self):
        """Valide le scan, décrémente les séances et enregistre le check-in."""
        self.ensure_one()
        if not self.card_id:
            raise UserError("Veuillez sélectionner une carte RFID.")

        # On récupère l'abonnement
        sub = self.env['amarna.subscription'].search([
            ('rfid_card_id', '=', self.card_id.id),
            ('active', '=', True),
        ], limit=1)

        if not sub or not sub.active or sub.state != 'sale' or sub.remaining_sessions <= 0:
            raise UserError("Une erreur est survenue : l'abonnement n'est plus valide pour le check-in.")

        # Sauvegarde des séances avant
        sessions_before = sub.remaining_sessions

        # Décrémenter et enregistrer
        sub.write({'remaining_sessions': sessions_before - 1})

        # Créer le check-in
        checkin = self.env['amarna.checkin'].create({
            'partner_id': sub.partner_id.id,
            'rfid_card_id': self.card_id.id,
            'activity_id': sub.activity_id.id if sub.activity_id else False,
            'sessions_before': sessions_before,
            'sessions_after': sessions_before - 1,
            'subscription_id': sub.id,
        })

        # Mettre à jour l'affichage du wizard
        self.remaining_sessions = sub.remaining_sessions
        self.result_state = 'success'
        self.result_message = (
            "✅ Accès autorisé\n"
            "Client : %s\n"
            "Activité : %s\n"
            "Séances restantes : %s"
        ) % (sub.partner_id.name, sub.activity_id.name if sub.activity_id else '', sub.remaining_sessions)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'amarna.scan.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
