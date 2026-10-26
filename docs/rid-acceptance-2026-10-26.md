# RID daily dam storage acceptance — 26 October 2026

Accepted product: `rid:daily_dam_storage`, 35 published large-dam reports. This acceptance covers daily reported storage, normal/maximum capacities and the published dam point locations. It does not accept flow rates, water levels, downstream risk, warning categories or other RID products.

## Evidence and scope

- Official documented GET: https://app.rid.go.th/reservoir/api/dam/public . Documentation: https://app.rid.go.th/reservoir/api/document/dam . The real 26 October response declares and contains 35 unique source IDs.
- Official reservoir interface: https://app.rid.go.th/reservoir/rsvmiddle . Its large-dam tab publishes matching identities, capacities and coordinates. A one-time, read-only query to the interface's `/reservoir/api/dams` supplied the static coordinate metadata. It is not a scheduled dependency. Only whitelisted identity and geographic fields are retained in `apps/web/data/rid-dams.json`; the capture checksum and source links are recorded there. No provider script, API key, logo or dashboard implementation is reused.
- All 35 identities join the documented daily response; all normal capacities agree between captures. All points have exactly one canonical province-polygon match. A district is assigned only when the point has one district match. Project regions are derived from canonical provinces; the separate `source_region` preserves RID's different grouping.
- Official RID publisher catalog: https://data.go.th/th/dataset/reservoir2 , dataset **ปริมาณน้ำไหลลงอ่างกักเก็บ**, description **ข้อมูลน้ำในอ่างเก็บน้ำ กรมชลประทาน**. Its unrestricted resource `cf31fdf3-b07d-4eec-8b74-706f1ed25bc7` links to the same reservoir interface (including the large-dam tab) and identifies Open Data Common reuse.
- DGA reuse terms: https://data.go.th/th/pages/dga-open-government-license , version 1.0, 10 June 2021. English text: https://data.go.th/uploads/page_images/2021-06-11-053225.908526Terms-and-Conditions-for-DGA-Open-Government-LicenseEN04062021.pdf . These allow reuse of published data with attribution and preservation of meaning, subject to excluded rights such as logos and third-party material. The acceptance interprets the explicitly linked official reservoir interface and its daily-storage data as the catalog resource's scope; it does not infer a blanket license for all RID endpoints or assign an unspecified ODbL version.

Attribution is retained in the registry, methodology, records, metadata and test-fixture notice. No endorsement by RID or DGA is claimed.

## Measurement and time semantics

| Provider field | Accepted meaning |
|---|---|
| `storage` | Normal storage capacity, million m³ |
| `capacity` | Maximum capacity, million m³ |
| `volume` | Reported stored water volume, million m³ |
| `percent_storage` | Volume / normal storage capacity × 100; values above 100 are valid |
| top-level `date` | Report calendar date; exact observation time is not supplied |

`observed_at` stays null and `time_precision` is `date`. No midnight or 08:00 observation instant is invented. Retrieval and ingestion instants remain separate. `inflow` and `outflow` are excluded because the documentation does not establish their accumulation window and exact unit semantics. Missing measurements remain null; measured zero remains zero. A changed name/ID, shifted coordinate, impossible range or inconsistent percentage fails validation.

## Collection and display

One documented GET daily at 08:15 Asia/Bangkok, with at most four bounded attempts for transient transport/429/5xx errors. No numeric quota is published in the reviewed documentation; one daily request is a conservative policy, not a quota guarantee. Permanent HTTP errors and invalid JSON do not retry. Safe logs contain reason codes/status only.

All 35 known identities and one report date are required before atomic publication. Independent `dam_latest` A/B slots retain at most 70 documents, with separate control/status/lock keys from weather. A failed report retains the last complete generation. The read-only verifier checks full coverage, schema, identity indexes and retention for both products; it never creates indexes or changes pointers.

Freshness considers report date and retrieval separately: a report for today's Bangkok date retrieved within 30 hours is FRESH; a report at most two calendar days old retrieved within 48 hours is DELAYED; older reports are STALE. Future/invalid time is UNKNOWN, no records UNAVAILABLE. Refetching an old report cannot make it FRESH.

The layer starts off, clusters counts by project region in the national overview, and shows individual dam points when drilled into a region or zoomed in. Groups are navigation controls, not measurements at their displayed center. Filtering by administrative area means the dam point lies in that area; it does not mean its reservoir or downstream influence is confined there. Forecast-date changes leave the RID report date unchanged.

## Verification

The real 35-report capture is tested for identity, units, date-only precision, null/zero distinction and percentage consistency. Isolated synthetic cases verify >100% acceptance, invalid data rejection, bounded slots, rollback, weather independence and sanitized request failures. Browser and HTTP checks cover regional drill-down, report details and independent weather dates. Atlas publication and its post-write storage/index evidence are recorded separately in `execution-status.md` after the first production run.
