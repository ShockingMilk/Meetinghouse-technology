# Development Guide

## Requirements

- Linux workstation.
- Visual Studio Code.
- Git.
- Docker Engine.
- Docker Compose plugin.
- Python 3.12 or compatible local interpreter (optional).

## Open the workspace

Open:

meetinghouse-technology.code-workspace

in Visual Studio Code.

Install the recommended extensions when prompted.

## Configure the environment

Copy:

.env.example

to:

.env

Change DJANGO_SECRET_KEY to a unique random value.

Do not commit .env.

## Start the development site

From the repository root:

docker compose up --build -d

Open:

<http://127.0.0.1:8000/>

## Create the initial administrator

docker compose exec web python manage.py createsuperuser

Do not use a shared or default password.

## Database setup

docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate

## Run tests

docker compose exec web python manage.py test

## View application logs

docker compose logs -f web

## Stop the application

docker compose down

The named Docker volume is retained when the containers are stopped.

To delete the development database volume, use:

docker compose down -v

This deletes the volume and its database. Do not use that command
unless you intend to discard the local development data.
