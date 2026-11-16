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

## Conventions

- Selection keys equal the Dart enum names in the app (`checkedin`,
  `inProgress`, `available`…). Never translate them.
- Datetimes are naive UTC, as every Odoo Datetime. Dates are local days.
- `session_count = 0` on a plan means an unlimited formula.
- `billing_state` and `payment_valid` are stored; `subscription_status` is
  computed on read (it depends on today's date).

## Tests

Run on a scratch database only, never on the live one:

```bash
odoo -c odoo.conf -d <scratch_db> -u abonnement_amarna,amarna_club_reservations --test-enable --test-tags amarna --stop-after-init
```

`abonnement_amarna/tests/test_billing.py` covers the money path: subscribe,
invoice, partial and full payment, renewal, free plans, scan denial when unpaid,
reservation check-in gated on payment, and session decrement.
