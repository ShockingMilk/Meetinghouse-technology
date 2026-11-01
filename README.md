# Meetinghouse Technology

A Django application for documenting and supporting technology used in a meetinghouse. The management area requires sign-in; training pages are open without sign-in. The current proof of concept provides a management dashboard, a searchable equipment inventory, asset detail pages, and a training landing page.

> This is a local planning and documentation tool. It does not replace Church policy, FMG processes, or required authorization. Keep management endpoints off the public Internet; building public-network access is distinct from Internet access.

## What is implemented

- **Management dashboard** — counts total assets, active assets, and assets with ownership to verify.
- **Technology inventory** — search by asset name or inventory number; filter by category and ownership.
- **Equipment wizard** — add or edit equipment through six guided steps, save and resume an incomplete draft, add rooms in place, and confirm the complete record before saving.
- **Asset records** — view asset identity, location, status, connections, installed software, camera presets, and notes.
- **Administration** — Django admin at `/admin/` for managing records.
- **Training** — a starter page for audio, video/Zoom, printing, and assistive listening material.

The application is an early POC. The equipment wizard covers the core asset record; guided forms for connections, maintenance, software, camera presets, broadcast workflows, and building assessments remain planned. See [docs/INVENTORY.md](docs/INVENTORY.md) for inventory guidance and [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) for the staged roadmap.

## Who can access each part

The management and training areas have different access requirements:

| Area | Sign-in | Intended network availability |
| --- | --- | --- |
| Management dashboard (`/`), inventory (`/inventory/`), and Django administration (`/admin/`) | **Sign-in required.** These pages are for authorized technology administrators. | Available to administrators on both the public and private building networks, with the private network as the primary access route. |
| Training (`/training/`) | **No sign-in required.** Anyone who needs operating instructions should be able to open them directly. | Available on both networks, with the public network as the primary access route. |

Here, “public network” means the building's public network; it does not mean the public Internet. These are the intended access goals. The normal development site runs locally with both areas. The management deployment includes authenticated management areas and the no-login training page. The separate training deployment routes only to training and omits management, login, and administration URLs and links. Network routing and production deployment still need to be configured. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Run locally with Docker

### Requirements

- Docker Engine
- Docker Compose plugin

### Setup

1. Copy `.env.example` to `.env`.
2. Set `DJANGO_SECRET_KEY` in `.env` to a unique random secret. Do not commit `.env`.
3. Start the development server:

   ```sh
   docker compose up --build -d
   ```

4. Apply database migrations and create an administrator:

   ```sh
   docker compose exec web python manage.py migrate
   docker compose exec web python manage.py createsuperuser
   ```

5. Visit the parts of the site:

   - <http://127.0.0.1:8000/> — management dashboard; sign in with the administrator account.
   - <http://127.0.0.1:8000/inventory/> — equipment inventory; sign-in required.
   - <http://127.0.0.1:8000/admin/> — Django administration; sign-in required.
   - <http://127.0.0.1:8000/training/> — training page; **no sign-in required**.

To start the system again after stopping it, run `docker compose up -d` from the repository root. To stop it, run `docker compose down`; this retains the development database volume.

By default the site binds to localhost on port `8000`. Change `WEB_PORT` in `.env` to use another local port.

### Preview the training-only profile

This profile uses separate URL routing and displays no management or login navigation. Preview it locally with:

```sh
cp .env.training.example .env.training
# Set DJANGO_SECRET_KEY to a unique random secret in .env.training.
docker compose --env-file .env.training -f compose.training.yaml up --build -d
```

Open <http://127.0.0.1:8081/training/>. The root address redirects to training. This deployment profile does not share the management database volume. Stop it with `docker compose --env-file .env.training -f compose.training.yaml down`.

The training-only URL configuration serves only training routes; management, inventory, login, logout, and Django admin routes are not registered. The management production profile remains separate. Before deployment, configure each profile's allowed host names, TLS termination, and network bindings for the approved building network setup.

### Common commands

```sh
# Follow application logs
docker compose logs -f web

# Run the Django test suite
docker compose exec web python manage.py test

# Stop containers (database volume is retained)
docker compose down
```

The development database is stored in the named Docker volume `meetinghouse_data`. `docker compose down -v` deletes that volume and its database.

## Local Python setup (optional)

With Python 3.12 or compatible installed, create and activate a virtual environment, install dependencies, and use the development settings:

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
DJANGO_SETTINGS_MODULE=config.settings.development python manage.py migrate
DJANGO_SETTINGS_MODULE=config.settings.development python manage.py createsuperuser
DJANGO_SETTINGS_MODULE=config.settings.development python manage.py runserver
```

## Project map

```text
apps/                  Django management, inventory, and training apps
config/                Project URLs and environment settings
templates/             HTML templates
static/css/site.css    Shared application styles
docs/                  Architecture, development, deployment, policy, and inventory notes
```

## Data and security

- Development uses SQLite. Docker stores the database in a persistent named volume.
- Keep secrets, credentials, personal information, and sensitive network details out of the repository and inventory.
- Record ownership as unknown until verified. Equipment location alone does not establish ownership.
- Clerk computers are outside this project's inventory scope.
- Do not change managed network infrastructure without the required authorization.
- Keep the management deployment off the public Internet. Building public-network access is distinct from Internet access.
- Deploy public-network training with the separate training-only profile; do not include management routes or its database.

Read [docs/CHURCH_POLICY.md](docs/CHURCH_POLICY.md), [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md), and [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) before making operational or deployment changes.
