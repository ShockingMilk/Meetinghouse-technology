# Implementation Plan

This plan records the intended direction for the meetinghouse technology site and separates working features from planned work. The implementation follows the existing Django project and model definitions; it does not replace the inventory data model.

## Project goals

- Make building technology records practical to create and update while walking through the building, including on a phone.
- Keep public training instructions easy to open without a site login.
- Restrict equipment management to signed-in authorized users.
- Preserve Django Admin as a back-office tool and keep current inventory detail pages usable.
- Keep secrets and sensitive network information out of the repository and out of public training.

## Access and network assumptions

The website is intended to run on one approved host. Training and management are different application areas with different sign-in rules. The current deployment plans provide a combined management profile and an optional training-only profile. Network reachability is controlled separately by the approved building network configuration.

The public Wi-Fi is Church-managed and may use a captive portal or client isolation. Do not assume that public and private Wi-Fi clients can reach a host, or change managed network equipment or firewall rules without approval from the appropriate network administrator. The private Wi-Fi may have a changing password; the host should use an approved stable connection rather than relying on that client password.

| Network | Intended access |
| --- | --- |
| Public building Wi-Fi | Training without a website login; authorized administrators can also reach management after signing in. |
| Private building Wi-Fi | Training plus authenticated management and inventory; this is the primary management access path. |
| Public Internet | No management access. Public training availability beyond the building network requires a separately approved hosting decision. |

## Milestone 1 — Project foundation and visual pass

**Status: Complete**

- Document project setup and current POC capabilities in the README.
- Improve dashboard, inventory, and asset detail readability on desktop and mobile.
- Add search and category and ownership filters to inventory.
- Document the distinction between public training and authenticated management access.

## Milestone 2 — Mobile-first equipment wizard

**Status: Implemented; validation and user review remain**

The wizard is the main guided path for adding and editing equipment. It uses existing `Asset` and `Room` models, leaves Django Admin available, and does not add migrations.

1. **Room** — choose an existing room or leave it unassigned; add a missing room without leaving the wizard.
2. **Category** — choose from the existing asset categories.
3. **Equipment details** — inventory number, name, manufacturer, model, serial number, and physical location.
4. **Technical details** — lifecycle dates, documentation link, funding and approval notes, estimate, specification, dependencies, recommended action, and notes.
5. **Responsibility** — ownership, condition, status, and responsible party.
6. **Review and save** — validate the full record and ask for a final confirmation before writing the equipment record.

Draft behavior:

- Store drafts in the signed-in user's Django session so a partially entered equipment record is not added to inventory.
- Allow incomplete fields to be saved and resumed from the inventory page.
- Preserve entered values when navigating backward.
- Keep a new room if the equipment draft is later discarded; room quick-add is a separate, immediate save.
- Edit existing equipment through the same steps, keeping the existing record unchanged until final confirmation.

Before calling this milestone complete, run the wizard tests and manually review the workflow at phone and desktop widths, including incomplete drafts, invalid fields, duplicate inventory numbers, room quick-add, edit confirmation, and cancellation.

## Milestone 3 — Supporting inventory forms

**Status: Planned**

Build guided forms for the related models that currently have admin-only editing:

- Physical connections between assets, with compatibility left unverified until tested.
- Maintenance, testing, and repair history.
- Installed software and verification dates.
- PTZ camera presets, clearly identified as values stored on the camera and recalled with its physical remote.
- Broadcast workflow records that validate the existing direct-to-Zoom and OBS paths.
- Building technology assessments.

Use existing models and admin screens as the source of truth. Add migrations only when a real data requirement cannot be represented by current fields.

## Milestone 4 — Training content

**Status: Planned**

Replace the training landing-page placeholders with concise, task-based instructions for audio, video and Zoom, printing, and assistive listening. Training remains open without an application login. Exclude management records, credentials, member information, and sensitive network details.

## Milestone 5 — Deployment and operations

**Status: Planned**

- Confirm the host, stable approved network connection, address/name, and power/sleep behavior.
- Coordinate any cross-network access with the stake technology specialist and Church network support; do not change Church-managed network equipment independently.
- Verify that public Wi-Fi can reach only the intended training service and that private-network management access requires sign-in.
- Add protected database and application-data backups, restoration instructions, and a recorded release/update procedure.
- Do not put the management site on the public Internet. Decide separately whether training will be building-only or hosted more broadly.

The local Docker setup is for development and review. It is not evidence that the meetinghouse network will route to the host.

## Acceptance checklist for the current wizard

- [ ] Training opens without a website login from both approved building networks.
- [ ] Management and inventory require sign-in, including when opened from either building network.
- [ ] An unauthenticated visitor requesting the equipment wizard is sent to management sign-in.
- [ ] A signed-in user can add a room and see it selected in the current draft.
- [ ] A signed-in user can save an incomplete draft, leave, and resume it.
- [ ] Back navigation preserves entered values.
- [ ] Duplicate inventory numbers produce a clear validation message.
- [ ] No new or edited asset is committed before final confirmation.
- [ ] Cancelling an asset draft does not delete a room created separately.
- [ ] Existing list, search, filters, and asset detail pages continue to work.
- [ ] Wizard tests pass and the layout is usable at narrow and wide viewport sizes.
