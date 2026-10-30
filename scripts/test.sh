#!/usr/bin/env bash

# Run the Django test suite.

set -euo pipefail

cd "$(dirname "$0")/.."

docker compose exec web python manage.py test
