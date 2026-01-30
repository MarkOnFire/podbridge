<!-- SYNC: This file is mirrored at docs/AIRTABLE_CHEATSHEET.md -->
<!-- for developer reference. Keep both copies in sync. -->
# PBSWI AirTable Quick Reference

**Base ID:** `appZ2HGwhiifQToB6`
**Purpose:** Token-efficient lookups for editorial workflows

---

## Table ID Quick Reference

| Table | ID | Editorial Use |
|-------|-----|---------------|
| **Single Source of Truth** | `tblTKFOwTvK7xw1H5` | Episode metadata, descriptions, credits |
| **Projects** | `tblU9LfZeVNicdB5e` | Project context, status, team |
| **Segment Tracking** | `tblb6x1BhkdhKrmT6` | WI Life segments, digital shorts |
| **Contacts** | `tblJc6JpKVcmwg0XV` | Hosts, presenters, interviewees |
| **All Staff** | `tblEjbbFzmpGZgbXF` | Crew credits, producers |
| **Events** | `tblCpPOWjybPSycSt` | Event-related content context |

---

## Find Episode Metadata

**Table:** `tblTKFOwTvK7xw1H5` (Single Source of Truth)

### By Media ID
```json
{"filterByFormula": "{Media ID} = \"9UNP2005HD\""}
```

### By Project Name
```json
{"filterByFormula": "FIND(\"Wisconsin Life\", ARRAYJOIN({Project}))"}
```

### Key Fields for Editorial
```
Batch-Episode       → Working title
Release Title       → Final title
Short Description   → 90 char max
Long Description    → 350 char max
Media ID            → Unique identifier
Project             → Linked project record
Digital Premiere    → Online release date
Premiere Date/Time  → Broadcast premiere
Producer            → Staff credits
Host                → Contact records
Presenter           → Contact records
Approved for Use    → Publication ready (checkbox)
```

### Description Character Count Fields
```
SD Character Count  → Validates short desc < 90
LD Character Count  → Validates long desc < 350
```

---

## Find Project Context

**Table:** `tblU9LfZeVNicdB5e` (Projects)

### By Name
```json
{"filterByFormula": "{Project Name} = \"Wisconsin Life\""}
```

### Key Fields
```
Project Name        → Title
Status              → In Progress, Complete, etc.
Format              → Broadcast & Online, Online-Only, etc.
Priority            → Critical, Important, Committed
Single Source of Truth → Linked episodes
Project Coordinator → Primary contact
```

---

## Find Wisconsin Life Segments

**Table:** `tblb6x1BhkdhKrmT6` (Segment Tracking)

### By Status
```json
{"filterByFormula": "{Segment Status} = \"Production In Progress\""}
```

### Key Fields
```
Segment Title       → Segment name
Short Description   → 90 char
Long Description    → Extended description
Episode             → Parent episode links
Producer            → Staff links
Main Location City  → Location
Main Location County→ Wisconsin county
Topics              → Topic tags
Digital Premiere    → Online release date
```

---

## Find Contact Info

**Table:** `tblJc6JpKVcmwg0XV` (Contacts)

### By Name
```json
{"searchTerm": "John Smith"}
```

### Key Fields for Credits
```
Name                → Full name
First Name          → For title case
Last Name           → For title case
Title               → Job title
Organization        → Linked org
Associated Episodes → Episode appearances
Episode Presenter   → Presenter credits
```

---

## Find Staff for Credits

**Table:** `tblEjbbFzmpGZgbXF` (All Staff)

### By Name
```json
{"searchTerm": "Producer Name"}
```

### Key Fields
```
Name                → Staff name
Department          → Department
Role                → Job role
```

---

## Common Editorial Queries

### Episodes Ready for Description Review
```json
{
  "tableId": "tblTKFOwTvK7xw1H5",
  "filterByFormula": "AND({Approved for Use} = TRUE(), OR({Short Description} = BLANK(), {Long Description} = BLANK()))",
  "maxRecords": 20
}
```

### Episodes Premiering This Month
```json
{
  "tableId": "tblTKFOwTvK7xw1H5",
  "filterByFormula": "AND(IS_AFTER({Digital Premiere}, TODAY()), IS_BEFORE({Digital Premiere}, DATEADD(TODAY(), 30, 'days')))",
  "sort": [{"field": "Digital Premiere", "direction": "asc"}]
}
```

### WI Life Segments by Location
```json
{
  "tableId": "tblb6x1BhkdhKrmT6",
  "filterByFormula": "{Main Location County} = \"Dane\""
}
```

### Find All Episodes for a Project
```json
{
  "tableId": "tblTKFOwTvK7xw1H5",
  "filterByFormula": "FIND(\"University Place\", ARRAYJOIN({Project}))",
  "maxRecords": 50
}
```

---

## Program-Specific Table Patterns

### University Place Episodes
- Query SST with: `FIND("University Place", ARRAYJOIN({Project}))`
- Check: `Presenter` field for speaker info
- Note: No honorifics in titles per program rules

### Here and Now Interviews
- Query SST with: `FIND("Here and Now", ARRAYJOIN({Project}))`
- Check: `Host` and `Presenter` for interview participants
- Get: Party/location info from Contacts table if needed

### Wisconsin Life
- Query Segments table (`tblb6x1BhkdhKrmT6`) first
- Then SST for episode-level data
- Key: Location fields for regional context

### Garden Shows (GWQS, etc.)
- Query SST with project filter
- Check: `Topics` for plant/garden categories

---

## Fields to SKIP (Not Editorial-Relevant)

These fields exist but aren't needed for content editing:
```
Status for Transfer     → File management
MXF Delivered          → Technical operations
QC fields              → Quality control
Captioning Assignment  → Production workflow
Tech Checked?          → Technical review
Alert for Tech Check   → Operations
ProTrack               → Broadcast system
Media Manager          → Distribution system
```

---

## Efficient Query Patterns

### DO: Use Direct Filters
```json
{"filterByFormula": "{Media ID} = \"9UNP2005HD\""}
```

### DO: Limit Results
```json
{"maxRecords": 10}
```

### DO: Use Search for Fuzzy Matching
```json
{"searchTerm": "candles", "tableId": "tblTKFOwTvK7xw1H5"}
```

### DON'T: Fetch All Records
Avoid empty filters on large tables (SST has thousands of records)

### DON'T: Query Multiple Tables When One Will Do
SST has lookup fields from Projects - often no need to query both

---

## Field Value Quick Reference

### Status Values (Projects)
```
Not Started | In Planning | In Progress | Complete |
Post-Launch | Ongoing | On Hold | Delayed | Cancelled
```

### Segment Status Values
```
Not Confirmed | In Planning | Production In Progress |
Exported for Episode | Scheduled Online | Aired in Episode
```

### Format Values (Projects)
```
Online-Only | Broadcast & Online | Broadcast Only |
Event | General Operational Activity
```

### Priority Values
```
Critical | Important | Committed | Not Rated
```

---

## Cross-Reference Lookup Pattern

When you have an episode and need contact details:

1. **Get episode record** from SST with desired Media ID
2. **Extract Contact record IDs** from `Host`, `Presenter`, or `Taping Contact` fields
3. **Query Contacts table** with those record IDs using `get_record`

Example flow:
```
SST record → {Host: ["recXXX", "recYYY"]} →
Contacts.get_record("recXXX") → Full contact info
```

---

## Notes

- All table/field names are case-sensitive in filter formulas
- Linked record fields return arrays of record IDs
- Lookup fields may be read-only (can't update directly)
- Description character limits: Short=90, Long=350
- Use `describe_table` with `detailLevel: "identifiersOnly"` if you need field IDs
