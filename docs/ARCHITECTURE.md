# Meetinghouse Technology Architecture

## Purpose

Provide a maintainable system for documenting, managing, and supporting
building technology.

## Application components

- Management: private management dashboard.
- Inventory: assets, rooms, connections, software, maintenance, and assessments.
- Training: user-facing instructions and documentation.

## Development workstation

The Linux workstation is the primary development environment.

It hosts:

- Visual Studio Code.
- Git repositories.
- Docker Engine and Docker Compose.
- Local Django development containers.
- Testing and troubleshooting tools.

The workstation is not the meeting broadcast host.

## Broadcast host

The broadcast host is a separate computer used for the camera and Zoom feed.

It may be managed remotely using:

- SSH for command-line administration.
- XRDP or VNC when graphical desktop access is required.

## PTZ video path

PTZ camera -> J5 Connect TX -> wireless link -> J5 Connect RX
-> USB -> broadcast host.

The actual camera output connector, receiver USB behavior, supported
resolution, frame rate, and Linux compatibility must be verified.

## Optional OBS path

Receiver -> broadcast host -> OBS Studio -> OBS Virtual Camera -> Zoom.

OBS is optional. The direct receiver-to-Zoom workflow remains a
separate supported configuration.

## Data storage

Development data is stored in a Docker-managed volume.

Building-specific data, credentials, and secrets must not be committed
to Git.

## Future database

SQLite is used initially. Django's ORM provides a migration path to
PostgreSQL if the deployment grows.

## Deployment separation

Development and deployment settings are separate.

The private management application must not be exposed publicly.

A future public training deployment should use a separate
training-only deployment.
