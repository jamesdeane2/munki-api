import os
from dotenv import load_dotenv

load_dotenv()

MUNKI_REPO_PATH = os.environ.get('MUNKI_REPO_PATH', '/Users/Shared/munki_repo')
MAKECATALOGS_PATH = os.environ.get('MAKECATALOGS_PATH', '/usr/local/munki/makecatalogs')
API_KEY = os.environ.get('API_KEY', '')
FLASK_HOST = os.environ.get('FLASK_HOST', '0.0.0.0')
FLASK_PORT = int(os.environ.get('FLASK_PORT', 5050))
