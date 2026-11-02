# Training and Documentation

## Access model

Training guides are public and do not require a user account. This keeps
instructions easy to reach from both public and private networks. Management
tools, inventory records, authoring, and publication controls remain behind
management authentication on the private deployment.

The training-only deployment runs `config.settings.training` with
`config.training_urls`. Its database and persistent Docker volume are separate
from the management deployment. It has no management, inventory, login, or
Django admin URLs. Do not point it at the management database.

## Initialize the management deployment

Apply the app migrations and create the training editor group:

```sh
sudo docker compose exec web python manage.py migrate
sudo docker compose exec web python manage.py setup_training_permissions
```

Add the intended editors and reviewers to the **Technology Specialists**
group through Django administration. Django's normal user permissions still
apply; only grant publishing and review rights to trusted editors.

Training categories are added by the migration. Editors can manage active
categories from **Training guides → Categories**. Existing categories can be
seeded or refreshed with:

```sh
sudo docker compose exec web python manage.py seed_training_categories
```

## Write, review, and publish

1. Sign in to the private management workspace and open **Training guides**.
2. Create a guide, optionally starting from an operating, setup,
   troubleshooting, maintenance, or quick reference template.
3. Write the guide in Markdown. Preview before saving. Link only the relevant
   assets and rooms; the public guide displays their inventory number/name or
   room name/number, never serial numbers, notes, credentials, or network
   configuration.
4. Save the working copy and submit it for review. It remains private until a
   publication snapshot exists.
5. A reviewer records review notes and approves or returns the draft.
6. A publisher explicitly confirms publication. The public site serves the
   immutable published revision. Later edits remain a private working copy
   until reviewed and published. Archiving hides the guide but preserves its
   revision history.

Published guide URLs use a permanent slug. To remove a guide from the public
catalog, archive it; do not delete it. Restore an older revision to the working
copy, then review and publish it as a new revision.

## Publish to the separate training deployment

The management database is the authoring source. After publishing or archiving
guides, export the public catalog:

```sh
sudo docker compose exec web python manage.py export_training_catalog
sudo docker compose cp web:/app/data/training-catalog.json ./training-catalog.json
```

Transfer `training-catalog.json` to the training host using the organization's
approved secure file-transfer method. It contains only published Markdown,
category information, publication dates, and explicitly linked public-safe
asset/room references, plus slugs to hide when guides have been archived. It
does not contain drafts or general inventory records. Treat the export as
public content, while still protecting the transfer from accidental edits.

On the training host, first start the service once to create its container and
persistent data volume. Then copy in the new catalog, run the import, and
restart the service:

```sh
sudo docker compose -f compose.training.yaml up -d
sudo docker compose -f compose.training.yaml cp ./training-catalog.json training:/app/data/training-catalog.json
sudo docker compose -f compose.training.yaml exec training python manage.py migrate
sudo docker compose -f compose.training.yaml exec training python manage.py import_training_catalog
sudo docker compose -f compose.training.yaml restart training
```

The training deployment's independent database is initialized by its own
migrations. Importing a repeated catalog is safe: existing matching published
revisions are retained, while a content mismatch for the same revision fails
instead of altering history. Guides removed from the public catalog are
archived locally and become unavailable. The export/import step is explicit;
there is no background synchronization or scheduler.

Configure `.env.training` with a secret key and allowed hosts for the training
host. Bind the service to the intended interface using `TRAINING_BIND_ADDRESS`
and `TRAINING_PORT`. The default binding is `127.0.0.1:8081`; place it behind
the organization's approved TLS reverse proxy if it must be reachable across
the public network. Keep the training Docker volume persistent so its catalog
and database survive container replacement.

## Authoring and safety guidance

- Use plain-language steps, a clear purpose, and an escalation section.
- State who is authorized to perform maintenance or configuration tasks.
- Do not include passwords, account details, member information, confidential
  building details, or sensitive network configuration.
- Link to the asset or room instead of copying private record information into
  guide text.
- Markdown is rendered through an HTML sanitizer. Embedded scripts, frames,
  unsafe links, and unsafe HTML attributes are removed.
- Keep categories broad enough to browse, and use tags for narrower topics.
- Search covers published title, summary, body, category, and tags only.

## Implementation notes

Guide revisions are immutable snapshots. Public pages, category counts,
search, and catalog exports all use the current published snapshot; draft edits
do not leak into the public site. Changes to a guide's slug are prevented after
the first publication. Asset and room relationships use the existing inventory
models and add no inventory fields.

The training catalog is currently copied as a JSON file. It does not stream
changes automatically. The export contains approved guide text, and the
separate database stores its imported public copies; neither deployment
connects to the other's database.
