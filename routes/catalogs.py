import os
import plistlib
from flask import Blueprint, jsonify
import config

catalogs_bp = Blueprint('catalogs', __name__)

CATALOGS_DIR = os.path.join(config.MUNKI_REPO_PATH, 'catalogs')


def plist_to_dict(path):
    with open(path, 'rb') as f:
        return plistlib.load(f)


@catalogs_bp.route('/', methods=['GET'])
def list_catalogs():
    if not os.path.isdir(CATALOGS_DIR):
        return jsonify({'error': 'Catalogs directory not found'}), 404
    catalogs = [f for f in os.listdir(CATALOGS_DIR)
                if os.path.isfile(os.path.join(CATALOGS_DIR, f)) and not f.startswith('.')]
    return jsonify({'catalogs': catalogs})


@catalogs_bp.route('/<path:name>', methods=['GET'])
def get_catalog(name):
    path = os.path.join(CATALOGS_DIR, name)
    if not os.path.isfile(path):
        return jsonify({'error': 'Catalog not found'}), 404
    try:
        data = plist_to_dict(path)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
