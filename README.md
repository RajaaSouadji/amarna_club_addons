# Amarna Club – Odoo 17 addons

Backend of the Amarna Club. The tablet app (`Amarna-Club/`) talks to these
models over JSON-RPC; Odoo owns all business data and rules.

## Modules

| Module | Role |
|---|---|
| `abonnement_amarna` | **Core.** Activities, subscription plans and durations, subscriptions, reservation billing rules, **centralised billing** (`amarna.billing.mixin`), RFID cards, access rules, check-ins. Other modules depend on it. |
| `amarna_club_assets` | Equipment and the armory (weapons). |
| `amarna_club_interventions` | Incidents and maintenance tickets, shared with the tablet. |
| `amarna_club_inventory` | Consumables with low-stock thresholds. |
| `amarna_club_ecurie` | Horses: status, fatigue, vet and farrier care. |
| `amarna_club_pool` | Pool water-quality readings and conformity. |
| `amarna_club_reservations` | Reservation screens and menus (model owned by the core). |
| `amarna_club_all` | Meta-module that installs the whole suite. |

A module exists only where an activity owns a unique kind of data (see
`odoo17/prompt1.md`). Shooting, gym, padel and paintball reuse the shared
assets, reservations and inventory.

## Billing: one path for everything

Accounting is the single source of truth for money.

1. A **subscription** (per period) or a **reservation** (per booking) computes
   its amount from its lines or from the activity's price per person.
2. **Facturer** posts an `account.move` (customer invoice) linked back with
   `amarna_subscription_id` / `amarna_reservation_id` and `amarna_period_start`.
3. **Encaisser** opens the standard Odoo payment wizard on the open invoice.
4. The billing state (`to_invoice`, `unpaid`, `partial`, `paid`, `free`) is
   computed from those invoices for the **current period only**.
5. Every reconciliation fires `account.partial.reconcile` → the RFID access of
   the linked subscription or reservation is recomputed. Access therefore
   follows the books however the money came in.

Renewals start a new period and invoice it; access stays closed until that
invoice is paid. Reservations covered by a subscription cost nothing and check
in against its sessions. A reservation cannot be checked in while unpaid.

The **Facturation** menu lists every Amarna invoice, with an "À encaisser"
filter.

## Configuration: nothing is hard-coded

Every business rule is a setting the club admin can change in Odoo, under
**Configuration > Club Amarna** (and the Piscine, Écurie and Armurerie blocks
of the same page). The tablet reads them after sign-in through
`res.company.amarna_app_config()`; it keeps no copy of its own.

| Setting | Where | Used by |
|---|---|---|
| Default VAT, opening hours, default slot, booking horizon, default people count | Club Amarna | reservations, billing |
| Expiry warning, ticket due delay | Club Amarna | subscriptions, interventions |
| Support phone, e-mail, hours | Club Amarna | tablet help screen |
| Pool temperature, chlorine, pH, turbidity ranges and score weights | Piscine | pool readings |
| Fatigue alert and rested level, farrier and deworming intervals | Écurie | horses |
| Weapon cleaning interval | Armurerie | weapons |
| Report periods and the default period | Club Amarna | tablet reports |
| Staff, their Odoo account and their activities | Configuration > Personnel du club | interventions, tablet profile |
| Each activity's price and VAT, each plan's price and VAT | Activities, Plans | billing |
| Which dedicated screen an activity opens, and its shortcut label | Activity > Application tablette | tablet activity page |
| Pre-session control points (nets, inflatables...) | Configuration > Points de contrôle | paintball field |
| Gym machines, padel courts, weapons, pool equipment | Équipements Club (tagged with the activity code) | gym, padel, armory screens |

Gym machines and padel courts are equipment records: a machine is out of order
when its status is `broken` and cleaned today when its last maintenance date is
today; a court is busy when `inUse`, and Odoo stamps `in_use_since` itself.
Weapons carry an explicit `is_weapon` flag; nothing is guessed from a category
name. The paintball player count is the activity's occupancy, and a capacity of
0 means no limit, in Odoo and on the tablet.

Taxes live on the activity and on the plan (defaulting from the club VAT), not
on the auto-created products, so a change applies to the next invoice.

When a module adds a rule, it extends `res.company` with its own fields, a
settings block, and an override of `_amarna_app_config()` that adds a key.

## Sample data

The modules install **no** sample records except the structure of the six
activities (name, code, icon, dedicated screen). Sample occupancy, capacity,
staff names, equipment, horses, stock and pool readings are in each module's
`demo/` folder and load only on a database created with demo data. A real club
database starts empty and the admin fills it in.

What stays in the app is presentation only: colours, status and priority
wording (they mirror fixed Odoo selection keys), and the route of each
dedicated screen.

## Conventions

- Selection keys equal the Dart enum names in the app (`checkedin`,
  `inProgress`, `available`…). Never translate them.
- Datetimes are naive UTC, as every Odoo Datetime. Dates are local days.
- `session_count = 0` on a plan means an unlimited formula.
- `billing_state` and `payment_valid` are stored; `subscription_status` is
  computed on read (it depends on today's date).

## Langue

Tout est en français. Les libellés écrits dans le code le sont déjà ; les
libellés que les modèles héritent d'Odoo (Messages, Société, Devise, Activité…)
sont traduits par le fichier `i18n/fr.po` de chaque module. Après avoir ajouté un
champ ou un écran, régénérez les termes pour repérer les libellés restés en
anglais, puis traduisez-les dans `i18n/fr.po` :

```bash
odoo -c odoo.conf -d <base> --modules=<module> --i18n-export=<module>.pot --stop-after-init
```

Chargez les traductions avec `-u <module> --i18n-overwrite`.

## Tests

Run on a scratch database only, never on the live one:

```bash
odoo -c odoo.conf -d <scratch_db> -u abonnement_amarna,amarna_club_reservations --test-enable --test-tags amarna --stop-after-init
```

`abonnement_amarna/tests/test_billing.py` covers the money path: subscribe,
invoice, partial and full payment, renewal, free plans, scan denial when unpaid,
reservation check-in gated on payment, and session decrement.
