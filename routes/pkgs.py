import os
from flask import Blueprint, jsonify, send_file
import config

pkgs_bp = Blueprint('pkgs', __name__)

PKGS_DIR = os.path.join(config.MUNKI_REPO_PATH, 'pkgs')


def list_files(base_dir):
    result = []
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for fname in files:
            if not fname.startswith('.') and fname.endswith('.pkg'):
                full = os.path.join(root, fname)
                rel = os.path.relpath(full, base_dir)
                result.append(rel)
    return result


@pkgs_bp.route('/', methods=['GET'])
def list_pkgs():
    if not os.path.isdir(PKGS_DIR):
        return jsonify({'error': 'Pkgs directory not found'}), 404
    return jsonify({'pkgs': list_files(PKGS_DIR)})


@pkgs_bp.route('/<path:name>', methods=['GET'])
def get_pkg(name):
    path = os.path.join(PKGS_DIR, name)
    if not os.path.isfile(path):
        return jsonify({'error': 'Package not found'}), 404
    return send_file(path, as_attachment=True)
