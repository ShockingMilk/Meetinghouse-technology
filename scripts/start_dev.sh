#!/usr/bin/env bash

# Start the local development environment.

set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -f ".env" ]]; then
    echo "Missing .env file."
    echo "Copy .env.example to .env and configure it first."
    exit 1
fi

docker compose up --build -d

echo
echo "Development environment started."
echo "Open http://127.0.0.1:8000/"
