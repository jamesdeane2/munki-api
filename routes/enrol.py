"""Enrolment routing endpoint.

Adds a device serial to the correct conditional_item in the enrol manifest
(default: _AUTO_ENROL), so a newly-provisioned Mac picks up its site's
migration package on next Munki run.

All the safety logic lives in `assign_serial_to_manifest`, which is HTTP-free
and unit-testable against a copy of a real manifest.
"""

import os
import re
import shutil
import tempfile
import plistlib
from datetime import datetime

from flask import Blueprint, jsonify, request

import config
from routes.utils import plist_to_dict

enrol_bp = Blueprint('enrol', __name__)

MANIFESTS_DIR = os.path.join(config.MUNKI_REPO_PATH, 'manifests')
PKGSINFO_DIR = os.path.join(config.MUNKI_REPO_PATH, 'pkgsinfo')

# Apple serials are 10-12 uppercase alphanumerics. Adjust via ENROL_SERIAL_RE if needed.
SERIAL_RE = re.compile(os.environ.get('ENROL_SERIAL_RE', r'^[A-Z0-9]{10,12}$'))


class EnrolError(Exception):
    """Carries an HTTP status and optional structured detail back to the caller."""

    def __init__(self, message, status=400, **extra):
        super().__init__(message)
        self.message = message
        self.status = status
        self.extra = extra


def _package_exists(name, pkgsinfo_dir):
    """True if a pkgsinfo item with the given 'name' key exists in the repo."""
    if not os.path.isdir(pkgsinfo_dir):
        return False
    for root, dirs, files in os.walk(pkgsinfo_dir):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for fname in files:
            if fname.startswith('.'):
                continue
            try:
                data = plist_to_dict(os.path.join(root, fname))
            except Exception:
                continue
            if data.get('name') == name:
                return True
    return False


def _find_serial(conditional_items, serial):
    """Return the managed_installs names of any condition already referencing serial.

    Matches both `serial_number == "X"` and `serial_number CONTAINS "X"`.
    """
    hits = []
    pat = re.compile(r'serial_number\s*(?:==|CONTAINS)\s*"' + re.escape(serial) + r'"')
    for item in conditional_items:
        if pat.search(item.get('condition', '') or ''):
            hits.extend(item.get('managed_installs') or ['<unnamed condition>'])
    return hits


def _atomic_write_plist(path, data):
    """Write plist atomically: temp file in same dir, re-parse to validate, then replace."""
    dest_dir = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=dest_dir, prefix='.enrol-', suffix='.tmp')
    try:
        with os.fdopen(fd, 'wb') as f:
            plistlib.dump(data, f)
            f.flush()
            os.fsync(f.fileno())
        plist_to_dict(tmp)  # round-trip validation; raises if the write is malformed
        os.replace(tmp, path)
        tmp = None
    finally:
        if tmp and os.path.exists(tmp):
            os.remove(tmp)


def assign_serial_to_manifest(manifest_path, client, serial, create_if_missing=True,
                              pkgsinfo_dir=None, package_check=True, backup=True,
                              backup_dir=None):
    """Add `serial` to `client`'s condition in the enrol manifest.

    Order of operations:
      1. validate serial format
      2. reject if the serial is already assigned anywhere (the anti-duplicate guard)
      3. append to the client's existing condition, OR
      4. create a new condition for the client (only if its package exists)
      5. timestamped backup, then atomic write with round-trip validation

    Returns a dict describing the change. Raises EnrolError with an HTTP status.
    """
    serial = (serial or '').strip().upper()
    client = (client or '').strip()
    if pkgsinfo_dir is None:
        pkgsinfo_dir = PKGSINFO_DIR

    if not client:
        raise EnrolError('client is required', 400)
    if not SERIAL_RE.match(serial):
        raise EnrolError('serial must be 10-12 uppercase alphanumeric characters',
                         400, serial=serial)
    if not os.path.isfile(manifest_path):
        raise EnrolError('enrol manifest not found: %s' % os.path.basename(manifest_path), 404)

    data = plist_to_dict(manifest_path)
    items = data.setdefault('conditional_items', [])

    # (2) dedup across the entire manifest — prevents a serial landing in two sites
    already = _find_serial(items, serial)
    if already:
        raise EnrolError('serial already assigned', 409,
                         serial=serial, assigned_to=sorted(set(already)))

    # find the client's condition by its managed_installs name
    target = None
    for item in items:
        if client in (item.get('managed_installs') or []):
            target = item
            break

    if target is not None:
        target['condition'] = (target.get('condition', '') or '').rstrip() + \
            ' OR serial_number == "%s"' % serial
        action = 'appended'
    else:
        if not create_if_missing:
            raise EnrolError('no condition for client "%s"' % client, 404, client=client)
        if package_check and not _package_exists(client, pkgsinfo_dir):
            raise EnrolError('no migration package for client "%s" - build it first' % client,
                             422, client=client)
        items.append({
            'condition': 'hostname == "%s" OR serial_number == "%s"' % (client, serial),
            'managed_installs': [client],
        })
        action = 'created_condition'

    # (5) backup outside manifests/ so Munki never sees the .bak as a manifest
    if backup:
        if backup_dir is None:
            repo_root = os.path.dirname(os.path.dirname(manifest_path))
            backup_dir = os.path.join(repo_root, '.enrol_backups')
        os.makedirs(backup_dir, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d-%H%M%S')
        shutil.copy2(manifest_path,
                     os.path.join(backup_dir, '%s.%s' % (os.path.basename(manifest_path), ts)))

    _atomic_write_plist(manifest_path, data)

    return {'status': 'ok', 'action': action, 'client': client,
            'serial': serial, 'manifest': os.path.basename(manifest_path)}


@enrol_bp.route('/assign', methods=['POST'])
def assign():
    body = request.get_json(silent=True) or {}
    manifest_path = os.path.join(MANIFESTS_DIR, config.ENROL_MANIFEST)
    try:
        result = assign_serial_to_manifest(
            manifest_path,
            body.get('client'),
            body.get('serial'),
            create_if_missing=bool(body.get('create_if_missing', True)),
        )
        return jsonify(result), 200
    except EnrolError as e:
        return jsonify({'error': e.message, **e.extra}), e.status
    except Exception as e:  # noqa: BLE001 - surface unexpected failures as 500
        return jsonify({'error': str(e)}), 500
