import os
from flask import Blueprint, jsonify, request, send_file
import config
from routes.utils import safe_path, list_files

icons_bp = Blueprint('icons', __name__)

ICONS_DIR = os.path.join(config.MUNKI_REPO_PATH, 'icons')
ICON_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.ico')


@icons_bp.route('/', methods=['GET'])
def list_icons():
    if not os.path.isdir(ICONS_DIR):
        return jsonify({'error': 'Icons directory not found'}), 404
    return jsonify({'icons': list_files(ICONS_DIR, extensions=ICON_EXTENSIONS)})


@icons_bp.route('/<path:name>', methods=['GET'])
def get_icon(name):
    try:
        path = safe_path(ICONS_DIR, name)
    except ValueError:
        return jsonify({'error': 'Invalid path'}), 400
    if not os.path.isfile(path):
        return jsonify({'error': 'Icon not found'}), 404
    return send_file(path)


@icons_bp.route('/<path:name>', methods=['POST'])
def upload_icon(name):
    if not name.lower().endswith(ICON_EXTENSIONS):
        return jsonify({'error': 'File must be an image (png, jpg, gif, ico)'}), 400
    try:
        path = safe_path(ICONS_DIR, name)
    except ValueError:
        return jsonify({'error': 'Invalid path'}), 400

    f = request.files.get('filedata') or request.files.get('file')
    if f is None:
        if request.content_length and request.content_length > 0:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'wb') as out:
                out.write(request.get_data())
        else:
            return jsonify({'error': 'No file provided'}), 400
    else:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        f.save(path)

    return jsonify({'status': 'ok', 'path': name}), 201


@icons_bp.route('/<path:name>', methods=['DELETE'])
def delete_icon(name):
    try:
        path = safe_path(ICONS_DIR, name)
    except ValueError:
        return jsonify({'error': 'Invalid path'}), 400
    if not os.path.isfile(path):
        return jsonify({'error': 'Icon not found'}), 404
    try:
        os.remove(path)
        return jsonify({'status': 'deleted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
