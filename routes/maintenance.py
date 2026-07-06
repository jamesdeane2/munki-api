"""Repo maintenance endpoints.

Exposes munki's official `repoclean` (manifest-aware, correct version
comparison) as an authenticated API call, so old software versions can be
pruned without SSH/shell access to the server.

POST /api/v1/maintenance/repoclean
    Body (JSON, all optional):
        keep   int   versions to keep per item        (default 1, min 1)
        apply  bool  actually delete + makecatalogs    (default False = dry-run)

    Dry-run returns what WOULD be removed; nothing is deleted unless apply=true.
"""
import os
import re
import subprocess
from collections import Counter

from flask import Blueprint, jsonify, request

import config
from routes.utils import run_makecatalogs, plist_to_dict

maintenance_bp = Blueprint('maintenance', __name__)

# repoclean ships alongside makecatalogs in the munki tools.
REPOCLEAN_PATH = os.path.join(os.path.dirname(config.MAKECATALOGS_PATH), 'repoclean')


def _parse_plan(text):
    """Parse repoclean output into a list of {name, version, pkginfo}."""
    dels = []
    current = None
    for line in text.splitlines():
        m = re.match(r'^name:\s*(.+?)\s*$', line)
        if m:
            current = m.group(1)
            continue
        if '[to be DELETED]' in line:
            pm = re.search(r'\(\s*(pkgsinfo/.+?\.plist)\s*\)', line)
            parts = line.strip().split()
            dels.append({
                'name': current,
                'version': parts[0] if parts else '?',
                'pkginfo': pm.group(1) if pm else None,
            })
    return dels


def _reclaimable_kb(dels):
    total = 0
    for d in dels:
        rel = d.get('pkginfo')
        if not rel:
            continue
        try:
            pk = plist_to_dict(os.path.join(config.MUNKI_REPO_PATH, rel))
            total += pk.get('installer_item_size', 0) or 0
        except Exception:
            pass
    return total


def _repo_size():
    try:
        r = subprocess.run(['du', '-sh', config.MUNKI_REPO_PATH],
                           capture_output=True, text=True, timeout=120)
        return (r.stdout.split() or ['?'])[0]
    except Exception:
        return '?'


@maintenance_bp.route('/repoclean', methods=['POST'])
def repoclean():
    if not os.path.isfile(REPOCLEAN_PATH):
        return jsonify({'error': f'repoclean not found at {REPOCLEAN_PATH}'}), 500

    body = request.get_json(silent=True) or {}
    try:
        keep = int(body.get('keep', 1))
    except (TypeError, ValueError):
        return jsonify({'error': 'keep must be an integer'}), 400
    if keep < 1:
        return jsonify({'error': 'keep must be >= 1'}), 400
    do_apply = bool(body.get('apply', False))

    # Dry-run plan: decline the prompt so repoclean lists but deletes nothing.
    try:
        plan = subprocess.run(
            [REPOCLEAN_PATH, '--keep', str(keep), config.MUNKI_REPO_PATH],
            input='n\n', capture_output=True, text=True, timeout=300)
    except Exception as e:
        return jsonify({'error': f'repoclean plan failed: {e}'}), 500

    dels = _parse_plan(plan.stdout + plan.stderr)
    counts = Counter(d['name'] for d in dels)
    result = {
        'keep': keep,
        'apply': do_apply,
        'items': len(counts),
        'pkginfos': len(dels),
        'reclaimable_gb': round(_reclaimable_kb(dels) / 1024 / 1024, 1),
        'by_item': dict(counts.most_common()),
    }

    if not dels:
        result['status'] = 'nothing-to-prune'
        return jsonify(result), 200
    if not do_apply:
        result['status'] = 'dry-run'
        return jsonify(result), 200

    # Apply: repoclean --auto, then makecatalogs.
    result['repo_before'] = _repo_size()
    try:
        r = subprocess.run(
            [REPOCLEAN_PATH, '--keep', str(keep), '--auto', config.MUNKI_REPO_PATH],
            capture_output=True, text=True, timeout=1800)
    except Exception as e:
        return jsonify({'error': f'repoclean --auto failed: {e}'}), 500
    if r.returncode != 0:
        return jsonify({'error': 'repoclean returned non-zero',
                        'stdout': r.stdout[-2000:], 'stderr': r.stderr[-2000:]}), 500

    run_makecatalogs()
    result['status'] = 'pruned'
    result['repo_after'] = _repo_size()
    return jsonify(result), 200
