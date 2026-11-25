#!/usr/bin/env bash
# Pull the latest addons, update the modules in the database, restart.
set -euo pipefail
cd "$(dirname "$0")"
DB="${1:-hasnaoui_amarna}"
git -C .. pull --ff-only
./setup.sh
docker compose pull
docker compose up -d db
docker compose run --rm -T odoo odoo -d "$DB" -u all --stop-after-init --no-http
docker compose up -d
