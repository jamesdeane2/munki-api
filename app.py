from flask import Flask, jsonify, request
import config
from routes.catalogs import catalogs_bp
from routes.manifests import manifests_bp
from routes.pkgsinfo import pkgsinfo_bp
from routes.pkgs import pkgs_bp
from routes.icons import icons_bp

app = Flask(__name__)


@app.before_request
def check_auth():
    # Allow CORS preflight through unauthenticated
    if request.method == 'OPTIONS':
        return None
    key = request.headers.get('X-API-Key')
    if not config.API_KEY or key != config.API_KEY:
        return jsonify({'error': 'Unauthorized'}), 401


app.register_blueprint(catalogs_bp, url_prefix='/api/v1/catalogs')
app.register_blueprint(manifests_bp, url_prefix='/api/v1/manifests')
app.register_blueprint(pkgsinfo_bp, url_prefix='/api/v1/pkgsinfo')
app.register_blueprint(pkgs_bp, url_prefix='/api/v1/pkgs')
app.register_blueprint(icons_bp, url_prefix='/api/v1/icons')


@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    print(f"Starting munki-api on {config.FLASK_HOST}:{config.FLASK_PORT}")
    print(f"Munki repo: {config.MUNKI_REPO_PATH}")
    print(f"\nEndpoints available at http://{config.FLASK_HOST}:{config.FLASK_PORT}/api/v1/")
    app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=False)
