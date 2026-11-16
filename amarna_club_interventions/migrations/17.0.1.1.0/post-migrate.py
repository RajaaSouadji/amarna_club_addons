# -*- coding: utf-8 -*-
"""Move tablet tickets pushed to ``maintenance.request`` into interventions.

Before this release the tablet pushed its tickets to the standard
``maintenance.request`` model while reading them back from
``amarna.club.intervention``, so the two sides never met. The records pushed
so far carry their data in the description (``[Mobile ID: ...]``, ``Type:``,
``Priority:``, ``Status:`` ...). This script copies each of them into
``amarna.club.intervention`` once. The original requests are left untouched.

Safe to run several times: a ticket already present (same ``mobile_id``) is
skipped, and nothing runs when the ``maintenance`` app is not installed.
"""
import logging
import re

from odoo import SUPERUSER_ID, api, fields

_logger = logging.getLogger(__name__)

MOBILE_ID_RE = re.compile(r'\[Mobile ID:\s*([^\]]+)\]')
TITLE_PREFIX_RE = re.compile(r'^\[[^\]]+\]\s*')
ACTIVITY_RE = re.compile(r'^Activity:.*\((\w+)\)\s*$', re.MULTILINE)
DUE_RE = re.compile(r'^Due At:\s*(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?)', re.MULTILINE)
ASSIGNED_RE = re.compile(r'^Assigned:\s*(.+)$', re.MULTILINE)
PRIORITY_RE = re.compile(r'^Priority:\s*(\w+)', re.MULTILINE)
STATUS_RE = re.compile(r'^Status:\s*(\w+)', re.MULTILINE)
TYPE_RE = re.compile(r'^Type:\s*(\w+)', re.MULTILINE)

TYPES = ('anomaly', 'preventive', 'corrective')
PRIORITIES = ('low', 'medium', 'high', 'critical')
STATUSES = ('open', 'inProgress', 'resolved')


def _first(pattern, text, allowed=None):
    match = pattern.search(text or '')
    if not match:
        return None
    value = match.group(1).strip()
    if allowed is not None and value not in allowed:
        return None
    return value


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    if 'maintenance.request' not in env:
        _logger.info('amarna_club_interventions: maintenance app not installed, nothing to migrate')
        return

    Request = env['maintenance.request'].with_context(active_test=False)
    Intervention = env['amarna.club.intervention'].with_context(
        tracking_disable=True, mail_create_nolog=True)
    requests = Request.search([('description', 'ilike', '[Mobile ID:')])

    created = skipped = 0
    for request in requests:
        description = request.description or ''
        mobile_id = _first(MOBILE_ID_RE, description)
        if not mobile_id:
            skipped += 1
            continue
        if Intervention.search_count([('mobile_id', '=', mobile_id)]):
            skipped += 1
            continue

        due = _first(DUE_RE, description)
        if due:
            # Normalise "YYYY-MM-DD HH:MM" / ISO "T" separators for Odoo.
            due = due.replace('T', ' ')
            if len(due) == 16:
                due += ':00'
        elif 'schedule_date' in Request._fields and request.schedule_date:
            due = fields.Datetime.to_string(request.schedule_date)

        assigned = _first(ASSIGNED_RE, description)
        activity_code = _first(ACTIVITY_RE, description)
        status = _first(STATUS_RE, description, STATUSES) or 'open'

        vals = {
            'name': TITLE_PREFIX_RE.sub('', request.name or '').strip() or mobile_id,
            'description': description,
            'mobile_id': mobile_id,
            'type': _first(TYPE_RE, description, TYPES) or 'anomaly',
            'priority': _first(PRIORITY_RE, description, PRIORITIES) or 'medium',
            'status': status,
            'mobile_activity_code': activity_code,
            'date_due': due,
            'assigned_to': assigned,
        }
        Intervention.create(vals)
        created += 1

    _logger.info(
        'amarna_club_interventions: migrated %s ticket(s) from maintenance.request, %s skipped',
        created, skipped)
