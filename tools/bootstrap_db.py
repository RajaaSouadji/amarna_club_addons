#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create a ready-to-use Amarna Club database (Algerian company, DZD, French).

The order matters: the company country and currency must be set BEFORE the
accounting module is installed, so that Odoo loads the Algerian chart of
accounts and VAT (l10n_dz). Once entries exist the currency can no longer be
changed, which is why this is a script and not a manual checklist.

    python tools/bootstrap_db.py --odoo-bin /path/odoo-bin \
        --config /etc/odoo.conf --db amarna_club [--sample-equipment]

Run it with the Python of the Odoo virtualenv. The database must not exist yet.
"""
import argparse
import os
import subprocess
import sys

COMPANY_SCRIPT = """
dz = env.ref('base.dz')
dzd = env.ref('base.DZD')
dzd.active = True
env.company.write({
    'name': %(name)r, 'country_id': dz.id, 'currency_id': dzd.id,
    'city': %(city)r, 'email': %(email)r, 'website': %(website)r,
})
env.ref('base.user_admin').write({'lang': 'fr_FR', 'tz': 'Africa/Algiers'})
env.cr.commit()
print('COMPANY_READY', env.company.name, env.company.currency_id.name)
"""


def run(cmd, stdin_text=None):
    print('>>', ' '.join(cmd), flush=True)
    result = subprocess.run(cmd, input=stdin_text, text=True, encoding='utf-8')
    if result.returncode:
        sys.exit('Command failed (exit %s)' % result.returncode)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--odoo-bin', required=True)
    parser.add_argument('--config', required=True)
    parser.add_argument('--db', required=True)
    parser.add_argument('--modules', default='amarna_club_all')
    parser.add_argument('--company-name', default='Amarna Club')
    parser.add_argument('--city', default='Alger')
    parser.add_argument('--email', default='contact@amarna-club.dz')
    parser.add_argument('--website', default='www.amarna-club.dz')
    parser.add_argument('--sample-equipment', action='store_true',
                        help='also load sample equipment and inventory records')
    args = parser.parse_args()

    base = [sys.executable, args.odoo_bin]
    common = ['-c', args.config, '-d', args.db]
    run(base + ['-i', 'base', '--load-language', 'fr_FR', '--stop-after-init'] + common)
    run(base[:2] + ['shell'] + common,
        COMPANY_SCRIPT % {'name': args.company_name, 'city': args.city,
                          'email': args.email, 'website': args.website})
    run(base + ['-i', args.modules, '--without-demo=True', '--stop-after-init'] + common)
    if args.sample_equipment:
        here = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(here, 'load_sample_equipment.py'), encoding='utf-8') as handle:
            run(base[:2] + ['shell'] + common, handle.read())
    print('Database %s is ready. Log in as admin and change the password.' % args.db)


if __name__ == '__main__':
    main()
