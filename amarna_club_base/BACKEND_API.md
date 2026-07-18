# Amarna Club Suite — Mobile App Backend Contract

The tablet app talks to Odoo through standard JSON-RPC
(`/web/session/authenticate` + `/web/dataset/call_kw/<model>/<method>`)
with the internal user **`amarna_mobile`** (groups: *Amarna Club / API
Mobile*). Credentials and model/field mappings live in the app's `.env`
(already generated). Every call below is verified end-to-end.

## Modules (each with its own root app in Odoo)

| Module | Root app | Model |
|---|---|---|
| `amarna_club_base` | Amarna Club | `amarna.club.activity` |
| `amarna_club_assets` | Équipements Club | `amarna.club.asset` |
| `amarna_club_interventions` | Interventions Club | `amarna.club.intervention` |
| `amarna_club_reservations` | Réservations Club | `amarna.club.reservation` |
| `amarna_club_inventory` | Inventaire Club | `amarna.club.inventory.item` |
| `amarna_club_ecurie` | Écurie | `amarna.club.horse` |
| `amarna_club_pool` | Piscine Club | `amarna.club.pool.reading` |
| `amarna_club_abonnement_link` | *(none, auto)* | link to `Abonnement`'s `amarna.activity` |
| `amarna_club_all` | *(umbrella)* | installs the whole suite |

All selection keys equal the app's Dart enum names verbatim
(`open`/`inProgress`/`resolved`, `available`/`inUse`/`maintenance`/`broken`,
`available`/`resting`/`injured`, `open`/`closed`/`warning`/`maintenance`).
Every model resolves `mobile_activity_code` (e.g. `pool`) to its
`activity_id` automatically.

## amarna.club.activity
`code`, `name`, `icon_key`, `mobile_status`, `current_occupancy` *(writable —
check-in bumps it)*, `max_capacity`, `assigned_staff`.

## amarna.club.asset
`code` (app asset id), `name`, `serial_number`, `category`,
`mobile_activity_code`, `status` *(writable)*, `last_maintenance`,
`next_maintenance` (weapons: cleaning due), `specs_json`, `is_weapon`
(computed from category containing "Arme").

## amarna.club.intervention  *(app pushes here — mapped in .env)*
`name`, `description` (the `[Mobile ID: …]` line is auto-extracted into
`mobile_id`; the `Type: …` line into `type`), `status`, `priority`,
`date_due`, `mobile_activity_code`, `assigned_to` (auto-matched to
`user_id`), `date_completed` (auto-set on resolve), `asset_id`.
Chatter enabled: comments/photos = the app's timeline.
Dedupe: `search_read([('description','ilike','[Mobile ID: X]')])`.

## amarna.club.reservation  *(app reads/writes here — mapped in .env)*
`name`, `start_at`, `end_at`, `mobile_activity_code`, `client_name`,
`people_count`, `status` (free text: `Confirme` / `En attente` / `Annule` /
`checkedin`), `status_normalized` (computed selection), `notes`,
optional `partner_id`. UI check-in button also bumps activity occupancy.

## amarna.club.inventory.item
`code`, `name`, `mobile_activity_code`, `qty` *(writable)*,
`low_threshold`, `unit`, `is_low` (computed).

## amarna.club.horse
`code`, `name`, `breed`, `age`, `box_number`, `status` *(writable)*,
`fatigue` (0–1, writable), `diet`, `vet_note`, `next_vet_visit`,
`last_farrier`, `last_vaccine`, `last_deworming`, `farrier_due` /
`deworming_due` (computed + searchable; 42 d / 90 d rules).
Riding sessions = reservations with `mobile_activity_code = 'horses'`.

## amarna.club.pool.reading
`reading_time`, `temperature`, `chlorine`, `ph`, `turbidity`, `author`,
computed `conform`, `issue_count`, `score` (app ranges: 26–30 °C,
1–3 mg/L, pH 7.2–7.6, ≤1 NTU; weights 20/30/30/20).

## Security
- *Utilisateur*: read/write/create on every club model (no delete).
- *Responsable*: full rights incl. delete.
- *API Mobile*: the tablet account's group (implies Utilisateur).
- PostgreSQL role `biuser`: direct read-only DB access (app health check).
No native Odoo module is modified anywhere in the suite.
