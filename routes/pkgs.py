import os
from flask import Blueprint, jsonify, request, send_file
import config
from routes.utils import safe_path, list_files, run_makecatalogs

pkgs_bp = Blueprint('pkgs', __name__)

PKGS_DIR = os.path.join(config.MUNKI_REPO_PATH, 'pkgs')
PKG_EXTENSIONS = ('.pkg', '.dmg')


@pkgs_bp.route('/', methods=['GET'])
def list_pkgs():
    if not os.path.isdir(PKGS_DIR):
        return jsonify({'error': 'Pkgs directory not found'}), 404
    return jsonify({'pkgs': list_files(PKGS_DIR, extensions=PKG_EXTENSIONS)})


@pkgs_bp.route('/<path:name>', methods=['GET'])
def get_pkg(name):
    try:
        path = safe_path(PKGS_DIR, name)
    except ValueError:
        return jsonify({'error': 'Invalid path'}), 400
    if not os.path.isfile(path):
        return jsonify({'error': 'Package not found'}), 404
    return send_file(path, as_attachment=True)


@pkgs_bp.route('/<path:name>', methods=['POST'])
def upload_pkg(name):
    if not name.lower().endswith(PKG_EXTENSIONS):
        return jsonify({'error': 'File must be .pkg or .dmg'}), 400
    try:
        path = safe_path(PKGS_DIR, name)
    except ValueError:
        return jsonify({'error': 'Invalid path'}), 400

    # Accept multipart file upload
    f = request.files.get('file') or request.files.get('filedata')
    if f is None:
        # Also accept raw body
        if request.content_length and request.content_length > 0:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'wb') as out:
                out.write(request.get_data())
        else:
            return jsonify({'error': 'No file provided'}), 400
    else:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        f.save(path)

    run_makecatalogs()
    return jsonify({'status': 'ok', 'path': name}), 201


@pkgs_bp.route('/<path:name>', methods=['DELETE'])
def delete_pkg(name):
    try:
        path = safe_path(PKGS_DIR, name)
    except ValueError:
        return jsonify({'error': 'Invalid path'}), 400
    if not os.path.isfile(path):
        return jsonify({'error': 'Package not found'}), 404
    try:
        os.remove(path)
        run_makecatalogs()
        return jsonify({'status': 'deleted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
