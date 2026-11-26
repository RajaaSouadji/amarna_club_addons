#!/usr/bin/env bash
# Update the server with the latest addons.
#
#   ./update.sh                    update every club module
#   ./update.sh mod_a,mod_b        update only these modules
#   PULL_IMAGES=1 ./update.sh      also pull newer Docker images (slow on this server)
#
# Odoo is stopped while the modules are updated, so nobody works on a half-updated database.
set -euo pipefail
cd "$(dirname "$0")"
DB="${DB:-hasnaoui_amarna}"
ALL="abonnement_amarna,amarna_club_assets,amarna_club_interventions,amarna_club_inventory,amarna_club_maintenance_stock,amarna_club_ecurie,amarna_club_pool,amarna_club_reservations,amarna_club_staff,amarna_club_theme,amarna_club_sms,amarna_club_all"
MODULES="${1:-$ALL}"

git -C .. pull --ff-only
./setup.sh
[ "${PULL_IMAGES:-0}" = 1 ] && docker compose pull
docker compose up -d db
docker compose stop odoo
# a module newly added to amarna_club_all is installed by the update of amarna_club_all
docker compose run --rm -T odoo odoo -d "$DB" -u "$MODULES" --stop-after-init --no-http
docker compose up -d odoo
