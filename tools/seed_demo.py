#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fill an Amarna Club database with realistic Algerian sample data.

Usage:
    python tools/seed_demo.py --url http://localhost:8070 --db amarna20_dz \
        --login admin --password admin

Needs only the Python standard library. It talks to Odoo over JSON-RPC, the same
way the tablet does, so it also exercises the real business rules (invoicing,
payment, check-in). It can be run again: records are found by name first.

Prerequisite: the database was created with `tools/bootstrap_db.py`
(Algerian company, DZD, chart of accounts and VAT).
"""
import argparse
import datetime as dt
import http.cookiejar
import json
import random
import unicodedata
import urllib.request

TODAY = dt.date.today()


class Odoo:
    def __init__(self, url, db, login, password):
        self.url = url.rstrip('/')
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.rpc('/web/session/authenticate',
                 {'db': db, 'login': login, 'password': password})

    def rpc(self, path, params):
        req = urllib.request.Request(
            self.url + path,
            json.dumps({'jsonrpc': '2.0', 'method': 'call', 'params': params}).encode(),
            {'Content-Type': 'application/json'})
        data = json.loads(self.opener.open(req, timeout=300).read())
        if data.get('error'):
            err = data['error'].get('data') or {}
            raise RuntimeError(err.get('message') or data['error'].get('message'))
        return data.get('result')

    def call(self, model, method, args=None, kwargs=None):
        return self.rpc('/web/dataset/call_kw/%s/%s' % (model, method), {
            'model': model, 'method': method,
            'args': args or [], 'kwargs': kwargs or {}})

    def search(self, model, domain, fields=('id',), **kw):
        kw.setdefault('context', {'active_test': False})
        return self.call(model, 'search_read', [domain], dict(fields=list(fields), **kw))

    def ensure(self, model, domain, vals):
        """Create the record, or update it when it already exists."""
        found = self.search(model, domain, limit=1)
        if found:
            self.call(model, 'write', [[found[0]['id']], vals])
            return found[0]['id']
        return self.call(model, 'create', [vals])


def day(offset):
    return (TODAY + dt.timedelta(days=offset)).isoformat()


def stamp(days=0, hours=0):
    base = dt.datetime.combine(TODAY, dt.time(8, 30))
    return (base + dt.timedelta(days=days, hours=hours)).strftime('%Y-%m-%d %H:%M:%S')


def slug(text):
    ascii_text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode()
    return ascii_text.lower().replace(' ', '.')


def log(*args):
    print(*args, flush=True)


# --------------------------------------------------------------------- data
ACTIVITIES = {
    # code: (name, unit price HT in DA per person, staff on duty, capacity)
    'pool': ('Piscine', 600, 'Samir Ouali (Maître-nageur)', 60),
    'horses': ('Équitation', 2500, 'Meriem Cherif (Responsable écurie)', 20),
    'shooting': ('Stand de Tir', 1800, 'Rachid Bouzid (Superviseur armurerie)', 12),
    'paintball': ('Paintball', 2200, 'Walid Taleb (Superviseur terrain)', 30),
    'gym': ('Salle de Gym', 800, 'Nadia Merabet (Coach)', 40),
    'padel': ('Terrains de Padel', 1600, 'Lina Hamidi (Coordinatrice padel)', 16),
}

STAFF = [
    # name, role, phone, activity codes, linked admin user
    ('Hakim Saadi', 'supervisor', '+213 550 12 34 56', list(ACTIVITIES), True),
    ('Mourad Haddad', 'technician', '+213 551 22 33 44', [], False),
    ('Sofiane Belkacem', 'technician', '+213 552 33 44 55', [], False),
    ('Yacine Amrani', 'technician', '+213 553 44 55 66', [], False),
    ('Samir Ouali', 'lifeguard', '+213 554 55 66 77', ['pool'], False),
    ('Meriem Cherif', 'horse_keeper', '+213 555 66 77 88', ['horses'], False),
    ('Rachid Bouzid', 'supervisor', '+213 556 77 88 99', ['shooting'], False),
    ('Walid Taleb', 'supervisor', '+213 557 88 99 00', ['paintball'], False),
    ('Nadia Merabet', 'instructor', '+213 558 99 00 11', ['gym'], False),
    ('Lina Hamidi', 'instructor', '+213 559 00 11 22', ['padel'], False),
]

DURATIONS = {'Hebdomadaire': (1, 'week'), 'Mensuel': (1, 'month'),
             'Trimestriel': (3, 'month'), 'Semestriel': (6, 'month'),
             'Annuel': (1, 'year')}

PLANS = [
    # name, activity, duration, sessions (0 = unlimited), price HT
    ('Piscine – Mensuel illimité', 'pool', 'Mensuel', 0, 6000),
    ('Piscine – Trimestriel illimité', 'pool', 'Trimestriel', 0, 16000),
    ('Piscine – Carte 10 séances', 'pool', 'Trimestriel', 10, 5000),
    ('Gym – Mensuel', 'gym', 'Mensuel', 0, 4500),
    ('Gym – Trimestriel', 'gym', 'Trimestriel', 0, 12000),
    ('Gym – Annuel', 'gym', 'Annuel', 0, 40000),
    ('Gym – Séance découverte (gratuite)', 'gym', 'Hebdomadaire', 1, 0),
    ('Padel – Mensuel illimité', 'padel', 'Mensuel', 0, 8000),
    ('Padel – Carte 10 séances', 'padel', 'Trimestriel', 10, 14000),
    ('Équitation – Forfait 8 séances', 'horses', 'Mensuel', 8, 18000),
    ('Équitation – Annuel illimité', 'horses', 'Annuel', 0, 150000),
    ('Tir – Carte 10 séances', 'shooting', 'Trimestriel', 10, 15000),
    ('Paintball – Pass saison', 'paintball', 'Annuel', 0, 9000),
]

MEMBERS = [
    'Mohamed Benali', 'Amina Boudiaf', 'Yacine Cherif', 'Fatima Zohra Belkacem',
    'Karim Hadjadj', 'Samia Mansouri', 'Redouane Meziane', 'Lydia Ait Ahmed',
    'Abdelkader Bouzid', 'Nawal Slimani', 'Tarek Zerrouki', 'Imane Ferhat',
    'Walid Khelifi', 'Sarah Benmoussa', 'Hichem Larbi', 'Meriem Guerroudj',
    'Oussama Rahmani', 'Khadidja Belaid', 'Anis Bensalem', 'Souad Kaci',
    'Billel Hamdani', 'Asma Touati', 'Zakaria Mebarki', 'Hanane Ouali',
    'Nassim Brahimi', 'Ines Boukhari', 'Ilyes Chikhi', 'Rania Dahmani',
    'Amine Saadi', 'Nesrine Lounis',
]
CITIES = ['Alger', 'Oran', 'Constantine', 'Blida', 'Annaba', 'Sétif',
          'Tizi Ouzou', 'Béjaïa', 'Batna', 'Tlemcen']

SUBSCRIPTIONS = [
    # member, plan, start offset in days, mode
    ('Mohamed Benali', 'Gym – Mensuel', -10, 'paid'),
    ('Amina Boudiaf', 'Piscine – Mensuel illimité', -18, 'paid'),
    ('Yacine Cherif', 'Padel – Mensuel illimité', -13, 'paid'),
    ('Fatima Zohra Belkacem', 'Piscine – Carte 10 séances', -34, 'paid'),
    ('Karim Hadjadj', 'Gym – Trimestriel', -69, 'paid'),
    ('Samia Mansouri', 'Équitation – Forfait 8 séances', -21, 'paid'),
    ('Redouane Meziane', 'Gym – Mensuel', -53, 'paid'),
    ('Lydia Ait Ahmed', 'Padel – Carte 10 séances', -11, 'unpaid'),
    ('Abdelkader Bouzid', 'Tir – Carte 10 séances', -29, 'paid'),
    ('Nawal Slimani', 'Gym – Annuel', -175, 'paid'),
    ('Tarek Zerrouki', 'Piscine – Trimestriel illimité', -5, 'uninvoiced'),
    ('Imane Ferhat', 'Gym – Séance découverte (gratuite)', -3, 'free'),
    ('Walid Khelifi', 'Paintball – Pass saison', -22, 'paid'),
    ('Sarah Benmoussa', 'Équitation – Annuel illimité', -83, 'partial'),
    ('Hichem Larbi', 'Gym – Mensuel', -3, 'draft'),
    ('Meriem Guerroudj', 'Padel – Mensuel illimité', -44, 'unpaid'),
    ('Oussama Rahmani', 'Piscine – Mensuel illimité', -8, 'cancelled'),
]

RESERVATIONS = [
    # activity, client, member, subscription holder, day, start, end, people, final status, invoice+pay
    ('padel', 'Yacine Cherif', 'Yacine Cherif', 'Yacine Cherif', 0, 18.0, 19.0, 4, 'checkedin', False),
    ('pool', 'Amina Boudiaf', 'Amina Boudiaf', 'Amina Boudiaf', 0, 10.0, 11.0, 1, 'checkedin', False),
    ('horses', 'Samia Mansouri', 'Samia Mansouri', 'Samia Mansouri', 0, 15.0, 16.0, 1, 'confirmed', False),
    ('paintball', 'Groupe Condor Electronics', None, None, 0, 14.0, 16.0, 12, 'checkedin', True),
    ('gym', 'Anis Bensalem', 'Anis Bensalem', None, 0, 17.0, 18.0, 1, 'pending', False),
    ('shooting', "Club de Tir Sportif d'Alger", None, None, 0, 16.0, 17.0, 6, 'confirmed', False),
    ('padel', 'Anniversaire de Nassim Brahimi', 'Nassim Brahimi', None, 1, 19.0, 20.5, 4, 'confirmed', True),
    ('pool', 'Fatima Zohra Belkacem', 'Fatima Zohra Belkacem', 'Fatima Zohra Belkacem', 1, 9.0, 10.0, 1, 'confirmed', False),
    ('paintball', 'Équipe Sonatrach Jeunes', None, None, 2, 10.0, 12.0, 18, 'confirmed', False),
    ('horses', 'Baptême à cheval – famille Rahmani', 'Oussama Rahmani', None, 2, 11.0, 12.0, 3, 'pending', False),
    ('padel', 'Ines Boukhari', 'Ines Boukhari', None, 3, 18.0, 19.0, 4, 'confirmed', True),
    ('gym', 'Hanane Ouali', 'Hanane Ouali', None, 3, 7.5, 8.5, 1, 'pending', False),
    ('shooting', 'Abdelkader Bouzid', 'Abdelkader Bouzid', 'Abdelkader Bouzid', 4, 10.0, 11.0, 1, 'confirmed', False),
    ('pool', 'École primaire Ibn Khaldoun', None, None, 5, 9.0, 11.0, 25, 'confirmed', True),
    ('padel', 'Rania Dahmani', 'Rania Dahmani', None, -1, 17.0, 18.0, 4, 'checkedin', True),
    ('paintball', 'Anniversaire de Zakaria Mebarki', 'Zakaria Mebarki', None, -2, 15.0, 17.0, 10, 'checkedin', True),
    ('horses', 'Souad Kaci', 'Souad Kaci', None, -1, 10.0, 11.0, 2, 'checkedin', True),
    ('padel', 'Ilyes Chikhi', 'Ilyes Chikhi', None, 2, 20.0, 21.0, 4, 'cancelled', False),
    ('gym', 'Amine Saadi', 'Amine Saadi', None, 6, 18.0, 19.0, 1, 'confirmed', False),
    ('pool', 'Nesrine Lounis', 'Nesrine Lounis', None, 7, 16.0, 17.0, 2, 'confirmed', True),
]

HORSES = [
    # name, breed, age, box, status, fatigue, diet, farrier/vaccine/deworming (days ago), vet note
    ('Sirocco', 'Barbe', 9, 'Box 1', 'available', 0.25, 'Foin et avoine, 6 kg/jour', (54, 95, 39), None),
    ('Tassili', 'Arabe-Barbe', 7, 'Box 2', 'available', 0.55, 'Foin, granulés, 5 kg/jour', (34, 79, 53), None),
    ('Hoggar', 'Barbe', 11, 'Box 3', 'resting', 0.82, 'Foin, avoine, compléments', (82, 134, 85),
     'Légère fatigue tendineuse, repos 5 jours.'),
    ('Atlas', 'Pur-sang arabe', 6, 'Box 4', 'available', 0.40, 'Foin, granulés, 5 kg/jour', (18, 44, 34), None),
    ('Zéphyr', 'Anglo-arabe', 8, 'Box 5', 'injured', 0.90, 'Foin, soins', (42, 114, 64),
     'Boiterie antérieure gauche. Examen vétérinaire en cours.'),
    ('Mouflon', 'Barbe', 13, 'Box 6', 'available', 0.18, 'Foin et avoine', (100, 69, 121), None),
]

TICKETS = [
    # title, activity, type, priority, status, technician, description, due offset
    ('Fuite sur la pompe de filtration n°2', 'pool', 'anomaly', 'high', 'inProgress',
     'Mourad Haddad', "Fuite d'eau visible au niveau du joint, pression en baisse.", 2),
    ('Vélo elliptique hors service', 'gym', 'anomaly', 'medium', 'open',
     'Yacine Amrani', "L'écran ne s'allume plus.", -1),
    ('Contrôle mensuel des filets de protection', 'paintball', 'preventive', 'medium', 'open',
     'Sofiane Belkacem', "Vérifier l'état et la tension des filets avant le week-end.", 2),
    ("Remplacement de l'éclairage du terrain 4", 'padel', 'corrective', 'low', 'open',
     'Yacine Amrani', 'Deux projecteurs grillés côté extérieur.', 5),
    ("Extracteur d'air du stand de tir en maintenance", 'shooting', 'corrective', 'critical',
     'inProgress', 'Mourad Haddad', "Débit insuffisant : tir suspendu jusqu'à réparation.", 1),
    ('Révision du système de chloration', 'pool', 'preventive', 'medium', 'resolved',
     'Sofiane Belkacem', 'Révision annuelle terminée, sondes recalibrées.', -4),
    ('Selle endommagée – couture déchirée', 'horses', 'anomaly', 'low', 'open',
     'Meriem Cherif', 'Selle à renvoyer chez le sellier.', 7),
    ('Vestiaires : robinet cassé', 'pool', 'anomaly', 'low', 'resolved',
     'Mourad Haddad', 'Robinet remplacé.', -7),
]

POOL_READINGS = [(-7, 28.5, 1.8, 7.4, 0.4), (-6, 28.9, 2.1, 7.5, 0.5),
                 (-5, 29.2, 2.4, 7.3, 0.4), (-4, 27.8, 0.8, 7.4, 0.6),
                 (-3, 28.1, 1.6, 7.7, 0.5), (-2, 28.6, 1.9, 7.4, 0.3),
                 (-1, 26.0, 2.0, 7.5, 1.3), (0, 28.4, 1.7, 7.4, 0.4)]


# -------------------------------------------------------------------- steps
def pay(odoo, invoice_ids, amount=None):
    """Register a payment through the standard Odoo wizard."""
    ctx = {'context': {'active_model': 'account.move', 'active_ids': invoice_ids}}
    vals = {} if amount is None else {'amount': float(amount)}
    wizard = odoo.call('account.payment.register', 'create', [vals], ctx)
    odoo.call('account.payment.register', 'action_create_payments', [[wizard]], ctx)


def seed_settings(odoo):
    taxes = odoo.search('account.tax', [('type_tax_use', '=', 'sale'), ('amount', '=', 19)],
                        ('name',))
    tax = next((t for t in taxes if t['name'] == '19% OS'), taxes[0] if taxes else None)
    if not tax:
        raise RuntimeError('No 19% sale tax: was the database created with bootstrap_db.py?')
    company = odoo.search('res.company', [], ('id',), limit=1)[0]['id']
    odoo.call('res.company', 'write', [[company], {
        'amarna_default_tax_id': tax['id'],
        'amarna_opening_hour': 8.0, 'amarna_closing_hour': 22.0,
        'amarna_default_start_hour': 9.0, 'amarna_default_end_hour': 10.0,
        'amarna_booking_horizon_days': 90, 'amarna_default_people_count': 2,
        'amarna_expiry_warning_days': 10, 'amarna_ticket_due_days': 3,
        'amarna_report_period_days': '7,30,90,365', 'amarna_report_default_days': 30,
        'amarna_support_phone': '+213 23 45 67 89',
        'amarna_support_email': 'support@amarna-club.dz',
        'amarna_support_hours': 'de 8h à 20h, du samedi au jeudi',
    }])
    odoo.call('res.users', 'write', [[2], {
        'name': 'Hakim Saadi', 'tz': 'Africa/Algiers',
        'email': 'h.saadi@amarna-club.dz'}])
    log('settings ok, default VAT =', tax['name'])
    return tax['id']


def seed_catalog(odoo, tax_id):
    tax = [(6, 0, [tax_id])]
    acts = {}
    for code, (name, price, staff, capacity) in ACTIVITIES.items():
        found = odoo.search('amarna.club.activity', [('code', '=', code)], limit=1)
        vals = {'name': name, 'unit_price': price, 'assigned_staff': staff,
                'max_capacity': capacity, 'tax_ids': tax}
        if found:
            acts[code] = found[0]['id']
            odoo.call('amarna.club.activity', 'write', [[acts[code]], vals])
        else:
            acts[code] = odoo.call('amarna.club.activity', 'create', [dict(vals, code=code)])
    for name, role, phone, codes, is_admin in STAFF:
        vals = {'name': name, 'role': role, 'phone': phone,
                'activity_ids': [(6, 0, [acts[c] for c in codes])]}
        if is_admin:
            vals['user_id'] = 2
        odoo.ensure('amarna.club.staff', [('name', '=', name)], vals)
    types = {}
    for name, (value, unit) in DURATIONS.items():
        types[name] = odoo.ensure('amarna.subscription.type', [('name', '=', name)],
                                  {'name': name, 'duration_value': value, 'duration_unit': unit})
    plans = {}
    for name, act, duration, sessions, price in PLANS:
        plans[name] = odoo.ensure('amarna.subscription.plan', [('name', '=', name)], {
            'name': name, 'activity_id': acts[act], 'subscription_type_id': types[duration],
            'session_count': sessions, 'list_price': price, 'tax_ids': tax})
    log('catalog ok:', len(acts), 'activities,', len(plans), 'plans')
    return acts, plans


def seed_members(odoo):
    random.seed(7)
    country = odoo.search('res.country', [('code', '=', 'DZ')])[0]['id']
    partners, cards = {}, {}
    for i, name in enumerate(MEMBERS):
        phone = '+213 %d %02d %02d %02d' % (
            random.choice([550, 551, 552, 553, 555, 556, 557, 660, 770, 771, 775]),
            random.randint(10, 99), random.randint(10, 99), random.randint(10, 99))
        partners[name] = odoo.ensure('res.partner', [('name', '=', name)], {
            'name': name, 'email': slug(name) + '@gmail.com', 'phone': phone,
            'city': CITIES[i % len(CITIES)], 'country_id': country})
    for name in MEMBERS[:20]:
        found = odoo.search('amarna.rfid.card', [('partner_id', '=', partners[name])], limit=1)
        cards[name] = found[0]['id'] if found else odoo.call('amarna.rfid.card', 'create', [{
            'partner_id': partners[name], 'state': 'active', 'assigned_date': day(-80)}])
    log('members ok:', len(partners), 'with', len(cards), 'cards')
    return partners, cards


def seed_subscriptions(odoo, partners, cards, plans):
    subs = {}
    for member, plan, offset, mode in SUBSCRIPTIONS:
        found = odoo.search('amarna.subscription', [('partner_id', '=', partners[member])], limit=1)
        if found:
            subs[member] = found[0]['id']
            continue
        vals = {'partner_id': partners[member], 'plan_id': plans[plan], 'start_date': day(offset)}
        if member in cards:
            vals['rfid_card_id'] = cards[member]
        try:
            sub = subs[member] = odoo.call('amarna.subscription', 'create', [vals])
            if mode == 'draft':
                continue
            odoo.call('amarna.subscription', 'action_confirm', [[sub]])
            if mode == 'cancelled':
                odoo.call('amarna.subscription', 'action_cancel', [[sub]])
            elif mode in ('paid', 'partial', 'unpaid'):
                odoo.call('amarna.subscription', 'action_create_invoice', [[sub]])
                invoices = odoo.search('amarna.subscription', [('id', '=', sub)],
                                       ('invoice_ids',))[0]['invoice_ids']
                if mode == 'paid':
                    pay(odoo, invoices)
                elif mode == 'partial':
                    pay(odoo, invoices, 50000)
        except Exception as exc:  # keep seeding the rest
            log('  subscription', member, plan, mode, 'FAILED:', str(exc)[:160])
    try:
        odoo.call('amarna.subscription', 'action_renew', [[subs['Redouane Meziane']]])
    except Exception as exc:
        log('  renewal skipped:', str(exc)[:120])
    odoo.call('amarna.subscription', 'cron_close_expired', [])
    log('subscriptions ok:', len(subs))
    return subs


def seed_reservations(odoo, partners, subs, acts):
    created = 0
    for act, client, member, holder, off, start, end, people, final, paid in RESERVATIONS:
        if odoo.search('amarna.club.reservation', [('client_name', '=', client)], limit=1):
            continue
        name = ACTIVITIES[act][0] + ' – ' + client
        vals = {'name': name, 'activity_id': acts[act], 'mobile_activity_code': act,
                'client_name': client, 'reservation_date': day(off), 'start_hour': start,
                'end_hour': end, 'people_count': people, 'status': 'pending'}
        if member:
            vals['partner_id'] = partners[member]
        if holder and holder in subs:
            vals['subscription_id'] = subs[holder]
        try:
            res = odoo.call('amarna.club.reservation', 'create', [vals])
            if final == 'pending':
                created += 1
                continue
            odoo.call('amarna.club.reservation', 'action_confirm', [[res]])
            if paid:
                odoo.call('amarna.club.reservation', 'action_create_invoice', [[res]])
                invoices = odoo.search('amarna.club.reservation', [('id', '=', res)],
                                       ('invoice_ids',))[0]['invoice_ids']
                pay(odoo, invoices)
            if final == 'checkedin':
                try:
                    odoo.call('amarna.club.reservation', 'action_check_in', [[res]])
                except Exception as exc:  # unpaid booking: refused by design
                    log('  check-in refused (expected):', client, '->', str(exc)[:90])
            elif final == 'cancelled':
                odoo.call('amarna.club.reservation', 'action_cancel', [[res]])
            created += 1
        except Exception as exc:
            log('  reservation', client, 'FAILED:', str(exc)[:160])
    log('reservations ok:', created)


def seed_operations(odoo, acts):
    # Horses: reuse the rows loaded by the demo data, create the missing ones.
    existing = odoo.search('amarna.club.horse', [], ('id',), order='id')
    for index, (name, breed, age, box, status, fatigue, diet, care, note) in enumerate(HORSES):
        vals = {'name': name, 'breed': breed, 'age': age, 'box_number': box,
                'status': status, 'fatigue': fatigue, 'diet': diet,
                'last_farrier': day(-care[0]), 'last_vaccine': day(-care[1]),
                'last_deworming': day(-care[2]), 'vet_note': note or False,
                'next_vet_visit': stamp(days=3) if status != 'available' else False}
        if index < len(existing):
            odoo.call('amarna.club.horse', 'write', [[existing[index]['id']], vals])
        else:
            odoo.ensure('amarna.club.horse', [('name', '=', name)], vals)
    for title, act, kind, prio, status, tech, desc, due in TICKETS:
        if odoo.search('amarna.club.intervention', [('name', '=', title)], limit=1):
            continue
        vals = {'name': title, 'activity_id': acts[act], 'mobile_activity_code': act,
                'type': kind, 'priority': prio, 'status': status, 'assigned_to': tech,
                'description': desc, 'date_due': stamp(days=due)}
        if status == 'resolved':
            vals['date_completed'] = stamp(days=due)
        odoo.call('amarna.club.intervention', 'create', [vals])
    if not odoo.call('amarna.club.pool.reading', 'search_count', [[('author', '=', 'Samir Ouali')]]):
        for off, temp, chlorine, ph, turbidity in POOL_READINGS:
            odoo.call('amarna.club.pool.reading', 'create', [{
                'reading_time': stamp(days=off, hours=-0.5), 'temperature': temp,
                'chlorine': chlorine, 'ph': ph, 'turbidity': turbidity,
                'author': 'Samir Ouali'}])
    log('operations ok: horses, tickets, pool readings')


def seed_scans(odoo, partners):
    """Badge a few members at the desk, through the same wizard the staff use."""
    done = 0
    for member in ('Mohamed Benali', 'Amina Boudiaf', 'Yacine Cherif', 'Karim Hadjadj',
                   'Fatima Zohra Belkacem', 'Samia Mansouri', 'Redouane Meziane'):
        card = odoo.search('amarna.rfid.card', [('partner_id', '=', partners[member])],
                           ('id',), limit=1)
        if not card:
            continue
        try:
            # The desk screen fills card_id from the typed code (onchange);
            # over RPC the card is given directly.
            wizard = odoo.call('amarna.scan.wizard', 'create', [{'card_id': card[0]['id']}])
            odoo.call('amarna.scan.wizard', 'action_scan', [[wizard]])
            odoo.call('amarna.scan.wizard', 'action_do_checkin', [[wizard]])
            done += 1
        except Exception as exc:  # unpaid or expired member: refused by design
            log('  scan not done:', member, '->', str(exc)[:80])
    log('scans ok:', done)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--url', default='http://localhost:8069')
    parser.add_argument('--db', required=True)
    parser.add_argument('--login', default='admin')
    parser.add_argument('--password', default='admin')
    args = parser.parse_args()
    odoo = Odoo(args.url, args.db, args.login, args.password)
    tax_id = seed_settings(odoo)
    acts, plans = seed_catalog(odoo, tax_id)
    partners, cards = seed_members(odoo)
    subs = seed_subscriptions(odoo, partners, cards, plans)
    seed_reservations(odoo, partners, subs, acts)
    seed_operations(odoo, acts)
    seed_scans(odoo, partners)
    log('done')


if __name__ == '__main__':
    main()
