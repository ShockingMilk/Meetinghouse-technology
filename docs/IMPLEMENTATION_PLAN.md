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

The wizard is the main guided path for adding and editing equipment. It uses existing `Asset` and `Room` models, leaves Django Admin available, and stores resumable drafts in the database.

1. **Room** — choose an existing room or leave it unassigned; add a missing room without leaving the wizard.
2. **Category** — choose from the existing asset categories.
3. **Equipment details** — inventory number, name, manufacturer, model, serial number, lifecycle and responsibility information, and category-specific notes.
4. **Connections** — optionally link existing equipment records.
5. **Review and save** — validate the full record and ask for a final confirmation before writing the equipment record.

Draft behavior:

- Store drafts in a user-owned database record so a partially entered equipment record is not added to inventory.
- Allow incomplete fields to be saved and resumed from the inventory page.
- Preserve entered values when navigating backward.
- Keep a new room if the equipment draft is later discarded; room quick-add is a separate, immediate save.
- Edit existing equipment through the same steps, keeping the existing record unchanged until final confirmation.

Before calling this milestone complete, run the wizard tests and manually review the workflow at phone and desktop widths, including incomplete drafts, invalid fields, duplicate inventory numbers, room quick-add, edit confirmation, and cancellation.

## Milestone 3 — Room assessment and room inventory integration

**Status: Implemented; generate and apply the RoomAssessment migration**

- Keep `Room` as the current room record and preserve assessment history in the separate `RoomAssessment` model.
- Show room priority, equipment count, latest assessment, and latest follow-up status in the room overview.
- Show assigned equipment, latest status, and dated assessment history on the room detail page.
- Add equipment from a room with that room preselected in the existing wizard.
- Filter inventory to equipment that is not assigned to a room.
- Require authentication for all room management and assessment views.
- Add an assessment without requiring existing equipment; a room may need an assessment to document missing technology.
- Preserve saved assessment history; existing assessments are read-only in Admin and cannot be deleted there.
- Cover the room overview, assessment creation, historical ordering, room-prefilled equipment wizard, and unassigned filter with inventory tests.

The assessment form captures overall, audio, video, network, printing, assistive-listening, and power status, observations, assessor, date, general notes, and follow-up. `Room.priority` remains the current room priority; the historical assessment does not rewrite room or asset data.

## Phase 2.4 — Maintenance and equipment lifecycle management

**Status: Implemented; run the generated inventory migration and full regression suite**

- Maintain dated service history with activity type, result, action, costs, and follow-up resolution.
- Support explicit recurring inspection schedules linked to completed maintenance records.
- Calculate due dates, follow-up states, and lifecycle warning windows when pages load; no task scheduler or notification infrastructure is used.
- Integrate maintenance summaries into asset and room detail pages and the authenticated management dashboard.
- Provide lifecycle review, replacement planning, and filtered CSV reporting with formula-injection protection.
- Preserve FMG authorization boundaries and never infer that a missing date is expired.

## Milestone 5 — Supporting inventory relationships

**Status: Implemented in Phase 2.5; migration generated, application and validation pending**

Provide authenticated management workflows for inventory relationships:

- Physical connections between assets, explicit dependencies, structured specifications, compatibility evidence, and replacement impact review.
- Installed software and verification dates.
- PTZ camera presets, clearly identified as values stored on the camera and recalled with its physical remote.
- Broadcast workflow records that validate the existing direct-to-Zoom and OBS paths.
- Building technology assessments.

Connections, dependencies, specifications, compatibility evidence, and replacement
reviews now have management views and asset/room integration. Installed software
and broadcast workflows remain the source of truth for software/workflow records.
Apply the generated inventory migration, then run system checks and the full test
suite before treating this milestone as validated.

## Phase 2.6 — Building technology dashboard and reporting

**Status: Implemented; Django checks and regression suite pending**

The authenticated overview now calculates inventory, room coverage, maintenance,
lifecycle, compatibility, attention priority, and recent activity summaries from
existing records. The management report area provides validated filters,
pagination, CSV export, and browser print layouts for inventory, rooms,
maintenance, lifecycle, compatibility, and ownership. The training-only URL
configuration remains limited to training pages. Validate the generated
Phase 2.5 migration and the full test suite in the project containers.

## Milestone 6 — Training content

**Status: Planned**

Replace the training landing-page placeholders with concise, task-based instructions for audio, video and Zoom, printing, and assistive listening. Training remains open without an application login. Exclude management records, credentials, member information, and sensitive network details.

## Milestone 7 — Deployment and operations

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

## Acceptance checklist for room assessments

- [ ] All room pages and assessment creation require sign-in.
- [ ] A room with no assigned assets can still be assessed.
- [ ] New assessments attach to the room in the URL and preserve earlier entries.
- [ ] Room overview shows each room's equipment count and latest assessment/follow-up state.
- [ ] Room detail shows assigned assets and the full assessment history.
- [ ] Adding equipment from a room preselects that room in the existing wizard.
- [ ] The inventory filter can show only unassigned equipment.
- [ ] Admin can review saved assessments but cannot edit or delete historical entries.
- [ ] Room assessment tests and Django system checks pass after migration `0003` is generated and applied.
