# munki-api

A Python Flask REST API that wraps a [Munki](https://github.com/munki/munki) repository, providing HTTP endpoints to browse and manage Munki repo contents over JSON. It exposes catalogs, manifests, pkgsinfo, packages, and icons — and automatically runs `makecatalogs` after any write operation to keep catalogs in sync.

## Requirements

- Python 3.8+
- A Munki repository on disk
- Munki tools installed (for `makecatalogs`, typically at `/usr/local/munki/makecatalogs`)

## Setup

```bash
git clone https://github.com/your-org/munki-api.git
cd munki-api
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your settings
```

## Configuration

All configuration is via environment variables (loaded from `.env` via `python-dotenv`).

| Variable             | Default                          | Description                                      |
|----------------------|----------------------------------|--------------------------------------------------|
| `MUNKI_REPO_PATH`    | `/Users/Shared/munki_repo`       | Absolute path to the root of the Munki repo      |
| `MAKECATALOGS_PATH`  | `/usr/local/munki/makecatalogs`  | Path to the `makecatalogs` binary                |
| `API_KEY`            | *(empty)*                        | API key required in `X-API-Key` header           |
| `FLASK_HOST`         | `0.0.0.0`                        | Interface Flask listens on                       |
| `FLASK_PORT`         | `5050`                           | Port Flask listens on                            |

## Running

**Using the helper script** (creates a virtualenv automatically):
```bash
./run.sh
```

**Directly:**
```bash
python app.py
```

The API will be available at `http://localhost:5050/api/v1/`.

## Authentication

All endpoints (except `/api/v1/health`) require an `X-API-Key` header matching the configured `API_KEY`:

```
X-API-Key: your-api-key-here
```

Requests without a valid key return `401 Unauthorized`. CORS preflight (`OPTIONS`) requests are also allowed through unauthenticated.

## API Endpoints

### Health

| Method | Endpoint           | Description                                      |
|--------|--------------------|--------------------------------------------------|
| GET    | `/api/v1/health`   | Returns repo status. **No auth required.**       |

### Catalogs

| Method | Endpoint                     | Description                                              |
|--------|------------------------------|----------------------------------------------------------|
| GET    | `/api/v1/catalogs/`          | List all catalog names. Add `?detail=true` to return full parsed plist data. Supports `?api_fields=` to limit returned keys. |
| GET    | `/api/v1/catalogs/<name>`    | Return the parsed contents of a specific catalog plist.  |

### Manifests

| Method        | Endpoint                        | Description                                                  |
|---------------|---------------------------------|--------------------------------------------------------------|
| GET           | `/api/v1/manifests/`            | List all manifests with full plist data. Supports field filtering via query params (e.g. `?catalogs=production`) and `?api_fields=` to limit returned keys. |
| GET           | `/api/v1/manifests/<name>`      | Return a specific manifest as JSON.                          |
| POST or PUT   | `/api/v1/manifests/<name>`      | Create or replace a manifest. Body: JSON plist data. Runs `makecatalogs`. |
| PATCH         | `/api/v1/manifests/<name>`      | Merge-update an existing manifest. Runs `makecatalogs`.      |
| DELETE        | `/api/v1/manifests/<name>`      | Delete a manifest. Runs `makecatalogs`.                      |

### Pkgsinfo

| Method        | Endpoint                        | Description                                                  |
|---------------|---------------------------------|--------------------------------------------------------------|
| GET           | `/api/v1/pkgsinfo/`             | List all pkginfo files with full plist data. Supports field filtering via query params and `?api_fields=`. |
| GET           | `/api/v1/pkgsinfo/<name>`       | Return a specific pkginfo file as JSON.                      |
| POST or PUT   | `/api/v1/pkgsinfo/<name>`       | Create or replace a pkginfo file. Body: JSON plist data. Runs `makecatalogs`. |
| PATCH         | `/api/v1/pkgsinfo/<name>`       | Merge-update an existing pkginfo file. Runs `makecatalogs`.  |
| DELETE        | `/api/v1/pkgsinfo/<name>`       | Delete a pkginfo file. Runs `makecatalogs`.                  |

### Packages

| Method | Endpoint                   | Description                                                        |
|--------|----------------------------|--------------------------------------------------------------------|
| GET    | `/api/v1/pkgs/`            | List all `.pkg` and `.dmg` files in the repo.                      |
| GET    | `/api/v1/pkgs/<name>`      | Download a package file.                                           |
| POST   | `/api/v1/pkgs/<name>`      | Upload a `.pkg` or `.dmg` (multipart `file`/`filedata` field, or raw body). Runs `makecatalogs`. |
| DELETE | `/api/v1/pkgs/<name>`      | Delete a package file. Runs `makecatalogs`.                        |

### Icons

| Method | Endpoint                    | Description                                                        |
|--------|-----------------------------|--------------------------------------------------------------------|
| GET    | `/api/v1/icons/`            | List all icon files (`.png`, `.jpg`, `.jpeg`, `.gif`, `.ico`).     |
| GET    | `/api/v1/icons/<name>`      | Serve an icon file.                                                |
| POST   | `/api/v1/icons/<name>`      | Upload an icon (multipart `file`/`filedata` field, or raw body).   |
| DELETE | `/api/v1/icons/<name>`      | Delete an icon file.                                               |

## Query Parameter Notes

- **`?api_fields=field1,field2`** — Available on list endpoints for catalogs, manifests, and pkgsinfo. Returns only the specified keys from each plist record.
- **Field filtering** — On `/api/v1/manifests/` and `/api/v1/pkgsinfo/`, any query parameter not named `api_fields` or `detail` is treated as a plist field filter (e.g. `?catalogs=production&display_name=Firefox`). List fields are matched by value; string fields use case-insensitive substring matching.

## launchd Service

A sample launchd plist (`com.github.munki-api.plist`) is included for running munki-api as a macOS service. Edit the paths as needed and load with `launchctl`.
