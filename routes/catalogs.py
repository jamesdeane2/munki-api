import os
from flask import Blueprint, jsonify, request
import config
from routes.utils import safe_path, plist_to_dict, enrich_plist_list

catalogs_bp = Blueprint('catalogs', __name__)

CATALOGS_DIR = os.path.join(config.MUNKI_REPO_PATH, 'catalogs')


@catalogs_bp.route('/', methods=['GET'])
def list_catalogs():
    if not os.path.isdir(CATALOGS_DIR):
        return jsonify({'error': 'Catalogs directory not found'}), 404
    api_fields = request.args.get('api_fields')
    # Catalogs are top-level plist arrays, not dicts with filenames.
    # Return enriched list if requested, otherwise simple list.
    if request.args.get('detail') == 'true':
        return jsonify(enrich_plist_list(CATALOGS_DIR, api_fields=api_fields))
    catalogs = [f for f in os.listdir(CATALOGS_DIR)
                if os.path.isfile(os.path.join(CATALOGS_DIR, f)) and not f.startswith('.')]
    return jsonify({'catalogs': catalogs})


@catalogs_bp.route('/<path:name>', methods=['GET'])
def get_catalog(name):
    try:
        path = safe_path(CATALOGS_DIR, name)
    except ValueError:
        return jsonify({'error': 'Invalid path'}), 400
    if not os.path.isfile(path):
        return jsonify({'error': 'Catalog not found'}), 404
    try:
        data = plist_to_dict(path)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
