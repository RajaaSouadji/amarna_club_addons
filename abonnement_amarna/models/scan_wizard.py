# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import format_amount


class AmarnaScanWizard(models.TransientModel):
    """Wizard de scan de carte RFID simulé dans Odoo.

    L'utilisateur sélectionne une carte RFID, puis clique sur "Scanner".
    Le système vérifie si la carte et l'abonnement sont valides et affiche
    les informations. L'utilisateur clique ensuite sur "Valider le scan"
    pour décrémenter une séance et enregistrer le check-in.
    """
    _name = 'amarna.scan.wizard'
    _description = 'Scan de carte RFID - Simulation'

    card_code = fields.Char(
        string='Numéro de carte',
        help="Passez la carte devant le lecteur ou saisissez son numéro, puis validez "
             "avec Entrée : la carte est reconnue et vérifiée aussitôt.",
    )
    card_id = fields.Many2one(
        'amarna.rfid.card',
        string='Carte reconnue',
        readonly=True,
        help="Carte trouvée à partir du numéro lu.",
    )

    # Informations du membre et de l'abonnement (affichées après le scan)
    partner_id = fields.Many2one('res.partner', string='Nom du client', readonly=True)
    partner_image = fields.Binary(related='partner_id.image_1920', string='Photo du membre')
    partner_phone = fields.Char(related='partner_id.phone', string='Téléphone')
    partner_email = fields.Char(related='partner_id.email', string='Email')

    subscription_ids = fields.Many2many(
        'amarna.subscription', string='Inscriptions de la carte', readonly=True,
    )
    subscription_id = fields.Many2one('amarna.subscription', string='Abonnement sélectionné')
    plan_id = fields.Many2one('amarna.subscription.plan', string='Formule', readonly=True)
    rfid_uid = fields.Char(string='UID RFID lu', readonly=True)
    activity_id = fields.Many2one('amarna.club.activity', string='Activité', readonly=True)
    subscription_type_id = fields.Many2one('amarna.subscription.type', string="Type d'abonnement", readonly=True)
    start_date = fields.Date(string='Date de début', readonly=True)
    expiration_date = fields.Date(string='Date de fin', readonly=True)
    remaining_sessions = fields.Integer(string='Séances restantes', readonly=True)
    is_unlimited = fields.Boolean(readonly=True)
    sessions_label = fields.Char(string='Séances', compute='_compute_sessions_label')
    card_state = fields.Selection([
        ('active', 'Accès ouvert'), ('inactive', 'Sans accès'), ('lost', 'Perdue'), ('blocked', 'Bloquée'),
    ], string='Statut carte', readonly=True)
    subscription_status = fields.Selection([
        ('draft', 'Brouillon'), ('active', 'Actif'), ('unpaid', 'Impayé'), ('expired', 'Expiré'), ('cancelled', 'Annulé'),
    ], string="Statut abonnement", readonly=True)

    currency_id = fields.Many2one('res.currency', string='Devise', readonly=True)
    payment_total = fields.Monetary(string='Total encaissé', currency_field='currency_id', readonly=True)
    payment_balance = fields.Monetary(string='Reste à payer', currency_field='currency_id', readonly=True)
    payment_valid = fields.Boolean(string='Paiement à jour', readonly=True)
    last_checkin_datetime = fields.Datetime(string='Dernier passage', readonly=True)

    result_state = fields.Selection([
        ('pending', 'En attente de scan'),
        ('ok', 'Prêt à valider'),
        ('denied', 'Accès refusé'),
        ('success', 'Accès autorisé'),
    ], default='pending', string='Résultat', readonly=True)

    result_message = fields.Text(string='Message', readonly=True)

    @api.depends('remaining_sessions', 'is_unlimited')
    def _compute_sessions_label(self):
        for wiz in self:
            wiz.sessions_label = 'Illimité' if wiz.is_unlimited else str(wiz.remaining_sessions)

    @api.onchange('card_code')
    def _onchange_card_code(self):
        """A reader types the card number then Enter: find the card and scan it."""
        code = (self.card_code or '').strip()
        self.card_id = False
        self.result_message = False
        if not code:
            self.result_state = 'pending'
            return
        card = self.env['amarna.rfid.card'].search([('name', '=ilike', code)], limit=1)
        if not card:
            self.result_state = 'denied'
            self.result_message = "❌ Carte inconnue : %s" % code
            return
        self.card_id = card
        self.action_scan()

    def action_scan(self):
        requested_subscription = self.subscription_id or self.env['amarna.subscription'].browse(
            self.env.context.get('default_subscription_id')
        )
        """Simule le scan de la carte sélectionnée."""
        self.ensure_one()
        if not self.card_id:
            raise UserError("Veuillez sélectionner une carte RFID.")

        # Réinitialisation des champs d'information
        self.partner_id = False
        self.subscription_ids = [(5, 0, 0)]
        self.subscription_id = False
        self.plan_id = False
        self.rfid_uid = False
        self.activity_id = False
        self.subscription_type_id = False
        self.start_date = False
        self.expiration_date = False
        self.remaining_sessions = 0
        self.card_state = False
        self.subscription_status = False
        self.currency_id = False
        self.payment_total = 0.0
        self.payment_balance = 0.0
        self.payment_valid = False
        self.last_checkin_datetime = False
        self.result_message = False

        # 1. Vérifier si la carte est active
        # An inactive card is normal when nothing is authorised right now: the
        # subscription checks below give the precise reason. Only an explicit
        # block or loss stops the scan here.
        if self.card_id.state in ('blocked', 'lost'):
            self.result_state = 'denied'
            self.result_message = "❌ Cette carte RFID est bloquée ou perdue."
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'amarna.scan.wizard',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
            }

        # 2. Rechercher l'abonnement actif lié à cette carte
        subscriptions = self.env['amarna.subscription'].search([
            ('rfid_card_id', '=', self.card_id.id),
            ('active', '=', True),
        ], order='activity_id, start_date desc')

        if not subscriptions:
            self.result_state = 'denied'
            self.result_message = "❌ Aucun abonnement actif trouvé pour cette carte."
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'amarna.scan.wizard',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
            }

        # Afficher toutes les inscriptions de cette carte et sélectionner
        # automatiquement la première formule actuellement utilisable.
        self.subscription_ids = [(6, 0, subscriptions.ids)]
        valid_subscriptions = subscriptions.filtered(
            lambda item: item.state == 'confirmed'
            and item.payment_valid
            and (not item.expiration_date or item.expiration_date >= fields.Date.today())
            and (item.is_unlimited or item.remaining_sessions > 0)
        )
        if requested_subscription and requested_subscription.id in subscriptions.ids:
            sub = requested_subscription
        else:
            sub = valid_subscriptions[:1] or subscriptions[:1]
        self.subscription_id = sub.id

        # 3. Vérifier les conditions de l'abonnement sélectionné
        if not sub.active or sub.state != 'confirmed':
            self.result_state = 'denied'
            self.result_message = "❌ Abonnement non confirmé (brouillon ou annulé)."
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'amarna.scan.wizard',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
            }

        if sub.is_frozen:
            self.result_state = 'denied'
            self.result_message = "❌ Abonnement suspendu jusqu'au %s." % sub.freeze_end
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'amarna.scan.wizard',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
            }

        if sub.expiration_date and sub.expiration_date < fields.Date.today():
            self.result_state = 'denied'
            self.result_message = "❌ Abonnement expiré (Échéance : %s)." % sub.expiration_date
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'amarna.scan.wizard',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
            }

        if not sub.payment_valid:
            self.result_state = 'denied'
            if sub.billing_state == 'to_invoice':
                self.result_message = "❌ Aucune facture émise pour cette période : facturez l'abonnement."
            else:
                self.result_message = "❌ Paiement en attente : reste à payer %s." % format_amount(
                    self.env, sub.amount_due, sub.currency_id)
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'amarna.scan.wizard',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
            }

        if not sub.is_unlimited and sub.remaining_sessions <= 0:
            self.result_state = 'denied'
            self.result_message = "❌ Solde épuisé (0 séance restante)."
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'amarna.scan.wizard',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
            }

        # 4. Rechercher le dernier passage (check-in) pour ce client
        last_checkin = self.env['amarna.checkin'].search([
            ('partner_id', '=', sub.partner_id.id),
        ], order='checkin_datetime desc', limit=1)

        # 5. Remplir les informations complètes du membre
        self.partner_id = sub.partner_id.id
        self.subscription_id = sub.id
        self.plan_id = sub.plan_id.id if sub.plan_id else False
        self.rfid_uid = self.card_id.name
        self.activity_id = sub.activity_id.id if sub.activity_id else False
        self.subscription_type_id = sub.plan_id.subscription_type_id.id if sub.plan_id and sub.plan_id.subscription_type_id else False
        self.start_date = sub.start_date
        self.expiration_date = sub.expiration_date
        self.remaining_sessions = sub.remaining_sessions
        self.is_unlimited = sub.is_unlimited
        self.card_state = self.card_id.state
        self.subscription_status = sub.subscription_status
        self.currency_id = sub.currency_id.id if sub.currency_id else False
        self.payment_total = sub.amount_paid
        self.payment_balance = sub.amount_due
        self.payment_valid = sub.payment_valid
        self.last_checkin_datetime = last_checkin.checkin_datetime if last_checkin else False

        self.result_state = 'ok'
        self.result_message = "✅ Carte et abonnement valides. Prêt à valider le scan."

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
        sub = self.subscription_id

        if (not sub or sub.rfid_card_id != self.card_id or not sub.active
                or sub.state != 'confirmed' or not sub.payment_valid
                or (not sub.is_unlimited and sub.remaining_sessions <= 0)):
            raise UserError("Une erreur est survenue : l'abonnement n'est plus valide pour le check-in.")

        # Sauvegarde des séances avant
        sessions_before = sub.remaining_sessions

        # Décrémenter (formule à séances uniquement) et enregistrer
        if not sub.is_unlimited:
            sub.write({'remaining_sessions': sessions_before - 1})

        # Créer le check-in
        checkin = self.env['amarna.checkin'].create({
            'partner_id': sub.partner_id.id,
            'rfid_card_id': self.card_id.id,
            'activity_id': sub.activity_id.id if sub.activity_id else False,
            'sessions_before': sessions_before,
            'sessions_after': sub.remaining_sessions,
            'subscription_id': sub.id,
        })

        # Mettre à jour l'affichage du wizard
        self.remaining_sessions = sub.remaining_sessions
        self.is_unlimited = sub.is_unlimited
        self.result_state = 'success'
        self.result_message = (
            "✅ Accès autorisé\n"
            "Client : %s\n"
            "Activité : %s\n"
            "Séances restantes : %s"
        ) % (sub.partner_id.name, sub.activity_id.name if sub.activity_id else '',
             'Illimité' if sub.is_unlimited else sub.remaining_sessions)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'amarna.scan.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
