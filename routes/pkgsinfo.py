import os
from flask import Blueprint, jsonify, request
import config
from routes.utils import (safe_path, plist_to_dict, dict_to_plist,
                          run_makecatalogs, enrich_plist_list)

pkgsinfo_bp = Blueprint('pkgsinfo', __name__)

PKGSINFO_DIR = os.path.join(config.MUNKI_REPO_PATH, 'pkgsinfo')


@pkgsinfo_bp.route('/', methods=['GET'])
def list_pkgsinfo():
    if not os.path.isdir(PKGSINFO_DIR):
        return jsonify({'error': 'Pkgsinfo directory not found'}), 404
    reserved = {'api_fields', 'detail'}
    filters = {k: v for k, v in request.args.items() if k not in reserved and v}
    api_fields = request.args.get('api_fields')
    return jsonify(enrich_plist_list(PKGSINFO_DIR, filters=filters or None,
                                     api_fields=api_fields))


@pkgsinfo_bp.route('/<path:name>', methods=['GET'])
def get_pkginfo(name):
    try:
        path = safe_path(PKGSINFO_DIR, name)
    except ValueError:
        return jsonify({'error': 'Invalid path'}), 400
    if not os.path.isfile(path):
        return jsonify({'error': 'Pkginfo not found'}), 404
    try:
        data = plist_to_dict(path)
        data['filename'] = name
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@pkgsinfo_bp.route('/<path:name>', methods=['POST', 'PUT'])
def write_pkginfo(name):
    try:
        path = safe_path(PKGSINFO_DIR, name)
    except ValueError:
        return jsonify({'error': 'Invalid path'}), 400
    data = request.get_json()
    if data is None:
        return jsonify({'error': 'Invalid JSON body'}), 400
    try:
        data.pop('filename', None)
        dict_to_plist(path, data)
        run_makecatalogs()
        return jsonify({'status': 'ok', 'path': name}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@pkgsinfo_bp.route('/<path:name>', methods=['PATCH'])
def patch_pkginfo(name):
    try:
        path = safe_path(PKGSINFO_DIR, name)
    except ValueError:
        return jsonify({'error': 'Invalid path'}), 400
    if not os.path.isfile(path):
        return jsonify({'error': 'Pkginfo not found'}), 404
    data = request.get_json()
    if data is None:
        return jsonify({'error': 'Invalid JSON body'}), 400
    try:
        existing = plist_to_dict(path)
        existing.update(data)
        existing.pop('filename', None)
        dict_to_plist(path, existing)
        run_makecatalogs()
        return jsonify({'status': 'ok', 'path': name}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@pkgsinfo_bp.route('/<path:name>', methods=['DELETE'])
def delete_pkginfo(name):
    try:
        path = safe_path(PKGSINFO_DIR, name)
    except ValueError:
        return jsonify({'error': 'Invalid path'}), 400
    if not os.path.isfile(path):
        return jsonify({'error': 'Pkginfo not found'}), 404
    try:
        os.remove(path)
        run_makecatalogs()
        return jsonify({'status': 'deleted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
