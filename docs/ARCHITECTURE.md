# Meetinghouse Technology Architecture

## Purpose

Provide a maintainable system for documenting, managing, and supporting
building technology.

## Application components

- Management: private management dashboard.
- Inventory: assets, rooms, connections, operational dependencies, structured
  specifications, compatibility evidence, software, maintenance, and assessments.
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

The training deployment uses `config.settings.training` and
`config.training_urls`, with its own SQLite database and persistent data
volume. It exposes only public training pages. It does not include management,
inventory, login, or Django admin routes. Editors publish guides in the private
management deployment; an explicit catalog export transfers only published
snapshots and their public-safe asset/room references to the training
deployment. The receiving database has its own copy of guide records and no
access to the management database. See [Training guide publishing](TRAINING.md)
for the operator workflow.

## Equipment relationship records

`AssetConnection` records a directional physical or logical link between two
inventory assets. Its uniqueness rule remains in place, and self-links are
rejected. Compatibility defaults to unknown and is never inferred from connector
names. `AssetDependency` separately records an operational requirement, because
a path between devices is not necessarily required for an asset to function.
Dependencies can target one inventory asset or a named external service; they
are directed from the dependent asset toward what it needs. New cycles are
rejected in the form/service validation layer, traversals use visited sets, and
existing cycles are reported for review.

`AssetSpecification` stores a category, name/value, verification state, and
optional evidence rather than adding category-specific nullable columns to
`Asset`. Existing manufacturer/model and free-text specification fields remain
the source for their current information. `CompatibilityVerification` preserves
dated evidence history. `ReplacementCompatibilityReview` stores a proposed
candidate and review outcome separately from inventory, and has no purchasing
or asset-status side effects.

The relationship views and services are part of the authenticated management
URL configuration only. `config.training_urls` includes training pages without
including inventory relationship routes. Dependency impact queries are bounded
by the set of visited assets; room pages include both endpoints even when the
other asset is in a different room or unassigned.

## Building dashboard and reports

The signed-in management overview calculates summaries on each request through
`apps.management.services.building_dashboard`. It reuses current assets, rooms,
room assessments, maintenance schedules and records, lifecycle fields, equipment
connections, dependencies, compatibility verifications, and replacement reviews.
It stores no warning flags or duplicate events. The training-only URL configuration
does not include management dashboards or reports.

`apps.management.reporting` owns the shared report querysets, row presentation,
headings, and CSV escaping. The paginated HTML report and CSV export apply the
same validated filters. CSV excludes free-text notes and network details. Printed
reports use browser print styles; the project does not generate PDF files.
