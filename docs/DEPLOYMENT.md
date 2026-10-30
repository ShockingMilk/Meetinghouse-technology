# Deployment Guide

## Development

The Linux workstation runs the development Docker Compose project.

The development environment is not the production environment.

## Deployment host

The eventual management deployment host should be selected and
approved before deployment.

## Management security

The management application is private.

Do not expose it to the public Internet.

Do not configure router port forwarding for the management site.

Use an approved network path and access controls.

## Future training deployment

If training content is later made available publicly, deploy a
separate training-only application.

Do not expose the management application as part of that deployment.

## Backups

Back up:

- The Django database.
- Uploaded documentation and media, if enabled.
- Deployment configuration.
- Required application data.

Keep backups protected and periodically test restoration.

## Changes

Test code on the development workstation before deployment.

Keep a record of deployed versions and changes.
