# Run inside `odoo-bin shell` on a seeded database:
#   odoo-bin shell -d <db> < tools/check_filters.py
# Evaluates every filter of every search view of the Amarna models, and the
# default filters of every Amarna action, and prints how many rows each gives.
# A filter that raises, or gives 0 on a seeded database, deserves a look.
from xml.etree import ElementTree as ET

from dateutil import relativedelta

from odoo import fields
from odoo.tools.safe_eval import datetime, safe_eval, time

ctx = {
    'datetime': datetime, 'time': time, 'relativedelta': relativedelta.relativedelta,
    'context_today': lambda: fields.Date.context_today(env.user),
    'current_date': fields.Date.context_today(env.user).strftime('%Y-%m-%d'),
    'uid': env.uid, 'user': env.user, 'company_id': env.company.id,
    'company_ids': env.companies.ids,
}
problems = 0
rows = []
actions = env['ir.actions.act_window'].search([('res_model', 'like', 'amarna')])
actions |= env.ref('abonnement_amarna.action_amarna_invoices', raise_if_not_found=False) or actions.browse()
for action in actions:
    Model = env[action.res_model]
    views = Model.get_views([(False, 'search')])
    arch = ET.fromstring(views['views']['search']['arch'])
    checks = [('(action domain)', action.domain or '[]')]
    for flt in arch.iter('filter'):
        if flt.get('domain'):
            checks.append((flt.get('name') or flt.get('string'), flt.get('domain')))
    base = safe_eval(action.domain or '[]', ctx)
    for name, domain in checks:
        try:
            count = Model.with_context(active_test=False).search_count(
                base + safe_eval(domain, ctx) if name != '(action domain)' else base)
            rows.append((action.name, name, count, ''))
        except Exception as exc:
            problems += 1
            rows.append((action.name, name, None, str(exc).splitlines()[0][:90]))
total = Model = None
for action_name, name, count, error in rows:
    flag = 'ERROR' if error else ('zero ' if count == 0 else 'ok   ')
    print('FILTER %s | %-34s | %-28s | %s %s' % (flag, action_name[:34], str(name)[:28], count, error))
print('FILTER_SUMMARY problems=%d zero=%d total=%d' % (
    problems, sum(1 for r in rows if r[2] == 0), len(rows)))
