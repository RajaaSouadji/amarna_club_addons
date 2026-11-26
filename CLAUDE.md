# CLAUDE.md — Amarna Club ERP (Odoo 20 addons)

Back-office of a sports club (gym, pool, padel, paintball, stable, armoury) on **Odoo 20**, plus the
Flutter tablet app (`Amarna-Club`, a sibling folder, not in this repository) that talks to it over
JSON-RPC. This repository holds only the addons. Branch `odoo20` is the live one.

## Modules (one Odoo app per module)

| Module | App / role |
|---|---|
| `abonnement_amarna` | core: members, subscriptions, billing, RFID cards, scan desk, payments, settings |
| `amarna_club_reservations` | bookings: one Planning page (calendar/list), waiting list, resources |
| `amarna_club_assets` | Matériel: equipment, maintenance journal, armoury register |
| `amarna_club_interventions` | Maintenance: tickets, preventive, teams |
| `amarna_club_inventory` | Stock: items, ledger, counts |
| `amarna_club_maintenance_stock` | bridge (auto-install): ticket parts leave stock |
| `amarna_club_ecurie` | Écurie: horses, care, boxes, boarding |
| `amarna_club_pool` | Piscine: water readings, tasks, incidents |
| `amarna_club_staff` | Personnel: certifications, shifts |
| `amarna_club_theme` | look and navigation only: app sidebar, home grid, top bar, chatter at the bottom |
| `amarna_club_sms` | SMS before a subscription ends (off by default, needs the Odoo `sms` module) |
| `amarna_club_all` | meta-module that installs everything |

`deploy/` = Docker setup of the server (see `deploy/README.md`). `tools/` = database bootstrap and demo data.

## Hard rules

1. **Never edit Odoo core** (`odoo20/`). Everything lives here: view inheritance, template extensions,
   JS registry patches. Check with `git -C <odoo20 folder> status` (must stay clean).
2. **The invoice is the source of truth for money.** Amounts due/paid come from `account.move`; the
   reconcile hook (`models/account_move.py`) refreshes RFID access however the payment arrives.
3. **Card access is derived, never typed.** `amarna.rfid.card.state` is computed: `Perdue`/`Bloquée`
   come from the manual `restriction`; `Accès ouvert`/`Sans accès` follow the authorisations of paid
   subscriptions and reservations. Do not add buttons that set it.
4. **Tablet contract.** The app mirrors Odoo selection keys verbatim. Before renaming a field or a key,
   grep `Amarna-Club/lib/services` and `lib/models`. Do not add a reservation status (the tablet reads
   every status of the day): the waiting list is its own model. Club settings reach the tablet through
   `res.company._amarna_app_config()`; add a key on both sides.
5. **Roles only decide menus.** ACL stay those of `group_club_user`; roles (Réception, Moniteur, Technique,
   Responsable) set which root apps are visible (`<record model="ir.ui.menu">` with `Command.clear()` +
   links: a `groups=` attribute on `<menuitem>` only *adds* groups on update). Mapping: `abonnement_amarna/security/security.xml`.
6. **Nothing leaves the building by default.** The partner-autocomplete widgets are turned back into plain
   fields (`amarna_club_theme/static/src/no_autocomplete`), SMS is off until enabled, onboarding tours are
   disabled (`amarna_club_theme/models/ir_http.py`). Keep it that way.
7. UI text is **French**. Add every new label to `i18n/fr.po` of its module (a stale `fr_FR` translation of
   a selection label survives a rename: reset it in SQL with `name - 'fr_FR'`).
8. **No credentials in this repository** (SSH, admin passwords, tokens). Ask the user.

## Odoo 20 gotchas met here

- Python: `models.Constraint` (not `_sql_constraints`), `<list>` (not `<tree>`, also in Python `view_mode`),
  `ir.access.csv` (not `ir.model.access.csv`), `group_ids` / `privilege_id` for groups, `aggregator`,
  `_read_group(..., ['__count'])`. A search method on a computed field receives `in`/`not in` with an
  OrderedSet value: normalise it. Search views and filters cannot use non-stored computed fields.
- Chatter: use `<chatter/>`, never the Odoo 17 `oe_chatter` div. Models without `name` need `_compute_display_name`.
- OWL 3: no `static props` on components, no `t-model` on a `proxy` state (use `t-att-value` + `t-on-input`),
  client actions go in `registry.category("actions")`. `<body>` itself is `.o_web_client`.
- Writes done in an `onchange` are not reliable: do side effects (check-in, invoices) in buttons or RPC methods.
- Asset bundles are cached in the DB: use `?debug=assets` while iterating, or `-u <module>` to rebuild.
  A new manifest file or Python file needs a server restart.
- `odoo-bin shell --no-http` for scripts; extra subcommand args go before `-c`.

## Run and test (local, Windows)

Workspace `C:\Users\<user>\Desktop\Repos\amarna\`: `odoo20\` (Odoo source), `odoo20-venv\`, `odoo20.conf`,
`start-odoo20.ps1`, `odoo20_addons\` (this repo, a worktree of the `odoo17/custom_addons` repository on
branch `odoo20`), `Amarna-Club\` (tablet). Server on port 8070, database `amarna20_new`; scratch database for
tests `amarna20_t1`. Absolute paths only: the shell tool's `cd` changes the working directory.

```
start-odoo20.ps1 --db-filter='^amarna20_new$' -d amarna20_new            # run
start-odoo20.ps1 -d amarna20_t1 -u <modules> --stop-after-init --no-http --test-tags amarna   # server tests (about 155)
start-odoo20.ps1 -d amarna20_new --stop-after-init --http-port=8071 --test-tags amarna_ui    # click-through of every app
```

Server-side tests alone once missed a broken kanban template: keep the click-through (`amarna_ui`, needs
Chrome and `websocket-client`) and look at new screens in the browser. Duplicate-key tracebacks in the test log
come from the uniqueness tests; `PermissionError ... .__gc` is a Windows filestore warning. Run tests on the
scratch database only. Fresh database: `tools/bootstrap_db.py` (Algerian company and DZD *before* accounting
installs), then `tools/seed_demo.py` (sample data over RPC).

## Server (10.20.10.49)

Odoo 20 and PostgreSQL 16 in Docker, the addons mounted from a clone in `/opt/amarna/addons` (branch `odoo20`).
Everything about it is in `deploy/README.md`. To update: push, then on the server stop Odoo, `git pull`,
run `-u <changed modules> --stop-after-init` in a one-off container, start Odoo (`deploy/update.sh`).
The VM disk is very slow (image pulls took ~35 min): do not pull images or run `-u all` casually, and never
update modules while the live container is running. The server has no backups by the owner's decision.

## Workflow

Commit in French, one feature per commit, trailer `Co-Authored-By`. Run the whole `amarna` test tag before pushing.
Do not push to or retarget `main` (the old Odoo 17 code base). The `odoo17/` folder and `_backup_*` in the
workspace are legacy: do not delete them without asking.
