import os
import plistlib
import subprocess
import config


def safe_path(base_dir, name):
    """Resolve path and verify it stays within base_dir."""
    full = os.path.realpath(os.path.join(base_dir, name))
    base = os.path.realpath(base_dir)
    if not full.startswith(base + os.sep) and full != base:
        raise ValueError("Path traversal detected")
    return full


def plist_to_dict(path):
    """Read a plist file and return a dict."""
    with open(path, 'rb') as f:
        return plistlib.load(f)


def dict_to_plist(path, data):
    """Write a dict as a plist file, creating parent dirs if needed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        plistlib.dump(data, f)


def list_files(base_dir, extensions=None):
    """Walk directory tree, return relative paths. Optionally filter by extension tuple."""
    result = []
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for fname in files:
            if fname.startswith('.'):
                continue
            if extensions and not fname.lower().endswith(extensions):
                continue
            full = os.path.join(root, fname)
            rel = os.path.relpath(full, base_dir)
            result.append(rel)
    return result


def run_makecatalogs():
    """Run makecatalogs against the configured repo path."""
    mc = config.MAKECATALOGS_PATH
    if os.path.isfile(mc):
        try:
            subprocess.run([mc, config.MUNKI_REPO_PATH],
                           capture_output=True, timeout=120)
        except Exception as e:
            print(f'WARNING: makecatalogs failed: {e}')
    else:
        print(f'WARNING: makecatalogs not found at {mc}')


def filter_fields(data, api_fields):
    """If api_fields query param is set, return only those keys from each dict."""
    if not api_fields:
        return data
    fields = [f.strip() for f in api_fields.split(',') if f.strip()]
    if not fields:
        return data
    if isinstance(data, list):
        return [{k: v for k, v in item.items() if k in fields} for item in data]
    if isinstance(data, dict):
        return {k: v for k, v in data.items() if k in fields}
    return data


def enrich_plist_list(base_dir, extensions=None, filters=None, api_fields=None):
    """Read all plists in a directory, return list of dicts with 'filename' injected.

    filters: dict of {field: value} to match against plist contents.
    api_fields: comma-separated string of fields to return.
    """
    results = []
    for rel_path in list_files(base_dir, extensions):
        full_path = os.path.join(base_dir, rel_path)
        try:
            data = plist_to_dict(full_path)
        except Exception:
            continue
        data['filename'] = rel_path

        # Apply filters
        if filters:
            match = True
            for key, value in filters.items():
                field_val = data.get(key)
                if field_val is None:
                    match = False
                    break
                # Handle list fields (e.g. catalogs, managed_installs)
                if isinstance(field_val, list):
                    if value not in [str(v) for v in field_val]:
                        match = False
                        break
                else:
                    if value.lower() not in str(field_val).lower():
                        match = False
                        break
            if not match:
                continue

        results.append(data)

    return filter_fields(results, api_fields)
