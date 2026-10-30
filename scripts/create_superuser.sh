#!/usr/bin/env bash

# Create an initial Django administrator interactively.

set -euo pipefail

cd "$(dirname "$0")/.."

docker compose exec web python manage.py createsuperuser
