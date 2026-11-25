#!/usr/bin/env bash
# First-time setup: random passwords in .env, and odoo.conf made from the template.
# Safe to run again: an existing .env is kept.
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -f .env ]; then
  umask 077
  printf 'DB_PASSWORD=%s\nADMIN_PASSWORD=%s\n' "$(openssl rand -hex 16)" "$(openssl rand -hex 16)" > .env
  echo ".env created"
fi
# shellcheck disable=SC1091
. ./.env
umask 077
sed -e "s/__ADMIN_PASSWORD__/${ADMIN_PASSWORD}/" -e "s/__DB_PASSWORD__/${DB_PASSWORD}/" odoo.conf.template > odoo.conf
# the container user (odoo, uid 101) must be able to read it
chmod 644 odoo.conf
echo "odoo.conf written"
