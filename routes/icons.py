import os
from flask import Blueprint, jsonify, send_file
import config

icons_bp = Blueprint('icons', __name__)

ICONS_DIR = os.path.join(config.MUNKI_REPO_PATH, 'icons')

ICON_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.ico')


def list_files(base_dir):
    result = []
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for fname in files:
            if not fname.startswith('.') and fname.lower().endswith(ICON_EXTENSIONS):
                full = os.path.join(root, fname)
                rel = os.path.relpath(full, base_dir)
                result.append(rel)
    return result


@icons_bp.route('/', methods=['GET'])
def list_icons():
    if not os.path.isdir(ICONS_DIR):
        return jsonify({'error': 'Icons directory not found'}), 404
    return jsonify({'icons': list_files(ICONS_DIR)})


@icons_bp.route('/<path:name>', methods=['GET'])
def get_icon(name):
    path = os.path.join(ICONS_DIR, name)
    if not os.path.isfile(path):
        return jsonify({'error': 'Icon not found'}), 404
    return send_file(path)
