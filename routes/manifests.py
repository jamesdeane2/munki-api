import os
import plistlib
import subprocess
from flask import Blueprint, jsonify, request
import config

manifests_bp = Blueprint('manifests', __name__)

MANIFESTS_DIR = os.path.join(config.MUNKI_REPO_PATH, 'manifests')


def run_makecatalogs():
    mc = config.MAKECATALOGS_PATH
    if os.path.isfile(mc):
        try:
            subprocess.run([mc], capture_output=True, timeout=120)
        except Exception as e:
            print(f'WARNING: makecatalogs failed: {e}')
    else:
        print(f'WARNING: makecatalogs not found at {mc}')


def plist_to_dict(path):
    with open(path, 'rb') as f:
        return plistlib.load(f)


def dict_to_plist(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        plistlib.dump(data, f)


def list_files(base_dir):
    result = []
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for fname in files:
            if not fname.startswith('.'):
                full = os.path.join(root, fname)
                rel = os.path.relpath(full, base_dir)
                result.append(rel)
    return result


@manifests_bp.route('/', methods=['GET'])
def list_manifests():
    if not os.path.isdir(MANIFESTS_DIR):
        return jsonify({'error': 'Manifests directory not found'}), 404
    return jsonify({'manifests': list_files(MANIFESTS_DIR)})


@manifests_bp.route('/<path:name>', methods=['GET'])
def get_manifest(name):
    path = os.path.join(MANIFESTS_DIR, name)
    if not os.path.isfile(path):
        return jsonify({'error': 'Manifest not found'}), 404
    try:
        data = plist_to_dict(path)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@manifests_bp.route('/<path:name>', methods=['POST', 'PUT'])
def write_manifest(name):
    path = os.path.join(MANIFESTS_DIR, name)
    data = request.get_json()
    if data is None:
        return jsonify({'error': 'Invalid JSON body'}), 400
    try:
        dict_to_plist(path, data)
        run_makecatalogs()
        return jsonify({'status': 'ok', 'path': name}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@manifests_bp.route('/<path:name>', methods=['DELETE'])
def delete_manifest(name):
    path = os.path.join(MANIFESTS_DIR, name)
    if not os.path.isfile(path):
        return jsonify({'error': 'Manifest not found'}), 404
    try:
        os.remove(path)
        run_makecatalogs()
        return jsonify({'status': 'deleted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
