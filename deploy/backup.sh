#!/usr/bin/env bash
# Daily backup: database dump + filestore, kept 14 days.
# cron: 30 2 * * * /opt/amarna/addons/deploy/backup.sh
set -euo pipefail
cd "$(dirname "$0")"
DB="${1:-hasnaoui_amarna}"
OUT="${BACKUP_DIR:-/opt/amarna/backups}"
STAMP="$(date +%F_%H%M)"
mkdir -p "$OUT"
docker compose exec -T db pg_dump -U odoo -Fc "$DB" > "$OUT/${DB}_${STAMP}.dump"
docker compose exec -T odoo tar -C /var/lib/odoo -czf - filestore > "$OUT/${DB}_${STAMP}_filestore.tar.gz"
find "$OUT" -type f -mtime +14 -delete
echo "backup ${STAMP} done"
