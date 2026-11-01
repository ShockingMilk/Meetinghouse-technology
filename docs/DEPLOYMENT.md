# Deployment Guide

## Development

The Linux workstation runs the development Docker Compose project.

The development environment is not the production environment.

## Deployment host

The eventual management deployment host should be selected and
approved before deployment.

## Access profiles

Management and training use separate production profiles.

### Management, inventory, and login

The management production profile includes the dashboard, inventory, login, and Django administration. All management and inventory views require sign-in. Make the site available to authorized administrators from the public and private building networks, primarily using the private network.

The management site must not be exposed to the public Internet. Do not configure Internet router port forwarding. Use approved network routing and access controls. `compose.production.yaml` binds the local reverse proxy to localhost by default; change `MANAGEMENT_BIND_ADDRESS` only to an approved host interface and put the required network controls in place.

### Training

Training pages require no sign-in. They should be available from both building networks, primarily the public network. “Public network” means the building's public network, not the public Internet.

Deploy training separately with `compose.training.yaml` and `config.settings.training`. This URL configuration registers only training routes and the template hides management, login, and administration navigation. Do not expose the full management deployment as a way to publish training. Bind the training service to the approved building network interface and enforce network access at the host firewall or network gateway.

The training service uses a distinct secret, URL configuration, and no persistent management database volume. Keep it separate from the management deployment and its data.

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
