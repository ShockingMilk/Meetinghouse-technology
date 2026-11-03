# Inventory Guidelines

## Asset identification

Each asset should have a unique inventory number.

Examples:

- COMP-0001: Broadcast host computer.
- VID-0001: PTZ camera.
- VID-0002: J5 Connect TX.
- VID-0003: J5 Connect RX.

These are examples, not confirmed building inventory records.

## Required information

Where available, record:

- Inventory number.
- Asset name.
- Category.
- Manufacturer.
- Model.
- Serial number.
- Ownership.
- Condition.
- Status.
- Room and physical location.
- Responsible party.
- Installation date.
- Warranty end date.
- End-of-life date.
- Security support end date.
- Last tested date.
- Documentation.
- Dependencies.
- Compatibility.
- Funding route.
- Approval status.
- Notes.

## Ownership

Use one of:

- FMG owned.
- Locally managed.
- Unknown - verify ownership.

Do not assume that equipment is locally managed because it is
physically located in the building.

## Camera presets

Record presets against the PTZ camera.

Do not treat the preset record as a command or software integration.
The camera stores and recalls its own positions.

## Connections

The guided equipment workflow can link a new record to existing assets. Select
the direction, connection type and medium, interface, compatibility, and notes
that are known. The workflow reuses existing inventory records and never creates
duplicate assets to represent a relationship. Review the connection before
confirming the equipment record. Existing connections are protected by a
database uniqueness rule; if a duplicate is selected, correct the draft and
retry.

Mark compatibility as unknown or unverified until tested. Do not include
passwords, network credentials, or confidential building information in notes.

## Connections, dependencies, and compatibility

Open **Compatibility** in the management workspace for building-wide search and
review. A connection describes a physical or logical path between two inventoried
assets (for example, a video link or USB connection). A dependency records what
an asset needs to operate. Dependencies can point to an inventoried asset or an
explicitly named external service/capability; do not create a fake asset for
Zoom, OBS, or another service. Record required versus optional dependencies and
the effect of a failure. Cycles are rejected for new dependency links; any
legacy cycles are shown for review and retained.

On an asset page, add structured technical specifications only when relevant to
that equipment category. Use separate facts such as interface, resolution,
frame rate, signal, connector, voltage, PoE, protocol, operating system, or
driver requirement. Leave values blank when unknown and use the verification
state and evidence reference to distinguish confirmed facts from assumptions.
The existing free-text specification field remains available for descriptive
notes; structured records do not duplicate manufacturer or model fields.

Compatibility checks are append-only evidence records. Select physical testing,
manufacturer documentation, specification review, vendor confirmation, or other
method; include the evidence reference and limitations when available. Same
connector names do not prove compatibility. Unknown stays unknown until checked.

For a replacement recommendation, open **Compatibility impact** from the asset
page. Review connected equipment, required and optional dependencies, reverse
and multi-level impact, interfaces, specifications, unverified facts, and prior
verification history. Record a candidate name/model and review state there;
this planning record does not create an inventory asset, approve a purchase, or
change equipment status. Only create an Asset after the item is acquired and
entered into inventory.

Room pages include relationships involving assets assigned to that room and
show the other endpoint's room or unassigned state. Portable and unassigned
assets remain visible in the building relationship view. The PTZ/J5/broadcast
host arrangement can be documented with asset connections and dependencies;
OBS Studio and Zoom can be documented as software/workflow or external service
dependencies. Do not enter unsupported resolutions, frame rates, or connector
claims as verified facts.

FMG-owned and unknown-ownership items can be documented as observed. Recording
does not authorize configuration changes or replacement of FMG-managed
equipment. Keep passwords, credentials, confidential Church/member information,
and sensitive network configuration out of specifications, evidence, and notes.

## Building dashboard and reports

Published guides that have been linked to an asset or room appear on that
record's management detail page. These links open the public-safe published
guide; private inventory fields are not copied into guide pages. See
[Training guide publishing](TRAINING.md) for writing and publishing guides.

The management overview is calculated from saved records when the page loads.
Its active inventory count means assets whose status is **Active**; retired
assets are excluded from active totals. The documented inventory total includes
all non-retired statuses, including stored, planned, under repair, and unknown.
Category, ownership, and condition totals use active assets; status totals include
all non-retired inventory. Stored and unassigned counts are shown separately.

Room coverage is assessed rooms divided by all recorded rooms. A room counts as
assessed when its latest room assessment has an overall status other than
**Unknown**. **Not Applicable** counts as an assessment because it is a recorded
assessment outcome. A room with no assessment is **Not assessed**, never failed.
The latest assessment date and status come from the existing append-only
`RoomAssessment` history; these calculated indicators do not replace the
assessment itself. Rooms do not currently have an active/inactive field, so all
recorded rooms are included.

Attention priorities are calculated from existing records: failed or most
recently reported offline equipment and confirmed incompatibility on required
connections/dependencies are **Critical**; overdue inspections, overdue follow-ups,
and unresolved reported issues are **High**; optional incompatibility, approaching
or passed lifecycle dates, and pending replacement decisions are **Medium**;
incomplete lifecycle fields are **Informational**. A passed warranty date does not
mean equipment failed, unknown dates do not count as expired, unknown compatibility
is not treated as incompatible, and an open follow-up alone does not mean equipment is unusable. Existing
`LIFECYCLE_WARNING_DAYS` and `MAINTENANCE_DUE_SOON_DAYS` settings control the
warning windows. No background jobs or notifications are used.

The management **Reports** page includes inventory, room inventory and assessment,
maintenance and inspections, lifecycle and replacement planning, compatibility,
and ownership reports. Use each report's available room, category, ownership,
status, condition, activity/result, compatibility, and date filters. Large report
tables show 50 rows per page. The report's CSV export uses the same filters and
dataset, includes column names and generation time, neutralizes spreadsheet
formula prefixes, and omits private free-text notes. To print, use the browser's
Print command; navigation and report controls are hidden in print layout. No PDF
or direct printer output is produced.

Replacement estimates are planning values only, separate from actual maintenance
costs; they do not represent an approved or funded purchase. FMG-owned equipment
remains subject to the ownership and authorization boundary described above.

## Guided equipment entry

Use **Add equipment** to start the five-step flow:

1. Choose a room or leave the equipment unassigned (for stored or portable items).
2. Choose an existing equipment category.
3. Record identity, lifecycle, ownership, condition, and technical notes. Use the
   existing specification field for readable category-specific observations.
4. Optionally connect the equipment to existing inventory records.
5. Review the complete entry and confirm before saving.

Drafts are persisted separately from inventory and are visible only to the
authenticated user who created them. Save a draft to pause, resume it from the
inventory page, or discard it there. All fields are validated again at final
save. Ownership defaults to **Unknown - Verify Ownership** and stays unknown
until verified. Django Admin remains available to authorized administrators as
a fallback.

## Physical identification labels

Use the unique inventory number as the equipment's physical identifier. Label
text follows this two-line pattern:

```text
CULTURAL HALL
AUDIO MIXER | AUDIO-0042
```

The room name is used as the heading when the asset is assigned to a room.
Unassigned equipment uses the configurable site heading, which defaults to
`MEETINGHOUSE TECH`. Set `ASSET_LABEL_SITE_HEADING` in the environment to change
that heading or leave it empty to omit it. Long equipment names are shortened
on the label line to keep the full inventory number readable; the full name is
shown on the on-screen reference page.

Open an equipment record and choose **Print label** for one item. To prepare a
batch, select the equipment rows in the inventory and choose **Print selected
labels**. The batch page sorts labels by inventory number. Printing or preparing
labels does not edit the asset record, and labels can be prepared again at any
time.

The Brother P-touch PT-D200 accepts Brother TZe tapes in 3.5, 6, 9, and 12 mm
widths, supports up to two text lines, and has a maximum print height of 9 mm
at 180 dpi. Use 9 mm or 12 mm tape for the two-line layout; 12 mm provides more
room for readable text. The label page is a text reference for manually entering
each line on the PT-D200. Choose a narrow margin if suitable, check the device's
own preview, and cut/apply the label using the printer's normal controls. The
website does not send jobs directly to the printer. Device-specific output has
not been tested with the physical label maker. See the [Brother PT-D200 product
specifications](https://www.brother-usa.com/p/label-makers/PTD200) and
[PT-D200 user's guide](https://www.brother-usa.com/-/media/brother/product-catalog-media/documents/2019/10/07/13/58/ptd200_useng_usr_laa723001a_print.pdf)
for supported media and margin details.

## Maintenance and equipment lifecycle

Open **Maintenance** from the management navigation for a calculated overview
of due inspections, unresolved follow-ups, lifecycle dates, and replacement
recommendations. The dashboard calculates these values when it loads; it does
not use notifications, background jobs, Celery, Redis, or a separate scheduler.

### Record maintenance

From an asset page choose **Record activity**, or use the Maintenance page to
record activity for an asset. Record the date, who performed or observed the
work, activity type, result, description, and action taken. Optionally include
materials, cost, and follow-up information. A maintenance record documents the
event; it never changes the asset's condition or status automatically.

If follow-up is required, describe the issue and optionally choose a due date.
Follow-ups remain open after their due date until a user records a resolution.
The record and asset remain available in maintenance history. A resolved issue
can be reopened if needed.

### Inspection schedules

Add schedules from an asset page or the maintenance overview. A schedule is an
explicit plan; the system does not create schedules automatically or invent
maintenance records. It calculates the next due date from the schedule's first
due date and the date of its latest associated maintenance record. Select the
related schedule when recording a completed inspection. Overdue schedules stay
visible until work is logged, the schedule is rescheduled, or it is disabled.

Suggested defaults are editable local planning intervals: audio six months,
assistive listening three months, video three months (and before important
broadcasts where appropriate), printers three months, locally managed network
equipment six months, and stored/portable equipment before use and every six
months. These suggestions are not Church policy or mandatory requirements. No
schedule is assigned automatically. For FMG-owned equipment, record observations
or review dates only unless required authorization is in place; the form asks
the user to acknowledge this boundary.

Set `MAINTENANCE_INTERVAL_*_MONTHS` in the environment to adjust the suggested
category intervals. `MAINTENANCE_DUE_SOON_DAYS` sets the inspection and follow-up
due-soon window (default 30 days).

### Lifecycle and replacement planning

Asset detail pages show warranty, security-support, and end-of-life dates as
current, approaching, expired, or not recorded. Missing dates remain unknown;
they are never treated as expired. `LIFECYCLE_WARNING_DAYS` controls the
approaching-date warning window (default 180 days). The detail view also shows
installation and last-tested dates, replacement estimate, recommendation, and
recommended action.

Recommendations include keep in service, monitor, repair, replace when budget
permits, replace as priority, retire, and verify manufacturer information. They
are planning notes only: they do not change equipment status or authorize a
purchase.

### Reports and CSV

The Maintenance **Reports** page supports maintenance history by asset and date
range, open follow-ups, overdue inspections, lifecycle review, and replacement
planning. Filter by asset, room, category, equipment status, or dates where
relevant, then choose **Download CSV**. CSV exports contain useful inventory and
maintenance fields but omit serial numbers and network configuration. Text that
could be interpreted as a spreadsheet formula is escaped on export.

Schedules and reports include assets without a room. Room detail pages summarize
each assigned asset's latest maintenance, upcoming or overdue inspections, open
follow-ups, and lifecycle review state. Maintenance records and schedules are
available only in the authenticated management deployment; the training-only
deployment does not expose them.

## Retired equipment

Retire equipment rather than deleting it. Historical maintenance
and connection records should remain available.
