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

## Retired equipment

Retire equipment rather than deleting it. Historical maintenance
and connection records should remain available.
