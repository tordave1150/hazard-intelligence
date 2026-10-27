# GISTDA supplied dictionary reconciliation — 2026-10-27

The supplied notes and six-sheet workbook were reviewed as reference evidence, not instructions to execute their proposed audit script, import raw responses, replace application contracts or activate a layer. Both original files in Downloads were read without editing/exporting them. The workbook was imported read-only with the bundled spreadsheet runtime. No additional API key was requested or read.

## Scope and evidence

| Reference | Confirmed scope | Effect on the project |
|---|---|---|
| Workbook `ArcGIS Verified Fields!A1:K15` | Seven fields for each of two public ArcGIS MapServer layers | Accepted as technical evidence for those exact ArcGIS resources only |
| Workbook `Endpoint Registry!A2:G5` | The separate Disaster Platform Features routes | Existing project evidence already verifies authorized 1day/30days responses, without establishing a stable provider contract for every product |
| Workbook `STAC Standard Only!A1:G13` and `Endpoint Registry!A8:G8` | Normative STAC fields and the catalog's one-day item URL | Existing authenticated one-day STAC inspection supplies observed metadata; normative fields still do not prove per-feature acquisition or that the footprint is a flood mask |
| Workbook `Integration Blockers!A2:D10` | Access, scientific meanings, product rights and operations questions | Access is already verified for the tested routes. Acquisition, units, coverage/quality, quota, complete-retrieval consistency and resource-specific display/retention rights remain open |
| Workbook `Internal Proposal!A1:D11` | Proposed internal fields and examples | Reference only; no example date, `raw_properties` proposal or field name overrides the project's contracts, redaction or persistence policy |

File hashes (SHA-256):

- `GISTDA_Data_Dictionary_Integration_Notes.md`: `881c416df4ae844fd349a9016fa50082a3d57771bd08cbb9473de5ca1e2368f6`
- `GISTDA_Verified_Data_Dictionary_2026-10-27.xlsx`: `2c58c778cb1fe792b3f905204140394b6abfb8da5fbccd13c272ec127b1210ff`

The workbook's "no current authorized response"/authentication-pending statements describe an independent reference review without the project's run evidence. They do not reset verified access or require a new key. See the [current Features review](gistda-disaster-features-review-2026-10-26.md) and [sample-quality report](gistda-geometry-readiness-2026-10-27.md). Only the tested combinations are confirmed; no 3day/7day, flood-frequency, water-hyacinth or tile service has been newly tested or substituted.

## Official ArcGIS metadata cross-check

Both primary metadata resources were fetched read-only, without authentication, feature queries or following redirects:

- [Layer 0 — พื้นที่ประสบภัยน้ำท่วม](https://gistdaportal.gistda.or.th/arcgis/rest/services/app/GISTDA_flood/MapServer/0?f=pjson)
- [Layer 1 — พื้นที่เสี่ยงภัยน้ำท่วม](https://gistdaportal.gistda.or.th/arcgis/rest/services/app/GISTDA_flood/MapServer/1?f=pjson)

All **14 field rows matched exactly** for field names, types, nullable flags, aliases and string length. Each layer exposes `objectid`, `f_area`, `tam_rai`, `shape`, `st_length(shape)`, `org_code`, `st_area(shape)`; `objectid` is non-nullable, the other six are nullable, and `org_code` has length 50. Each reports polygon geometry, `maxRecordCount=1000`, no date-type field, and no `timeInfo` in the inspected metadata.

The metadata adds a useful distinction beyond the notes: the service/extent reference has `wkid=102100`, `latestWkid=3857`, while **sourceSpatialReference is 32647**. [Esri documents that a layer's source reference may differ from the service/extent reference](https://developers.arcgis.com/rest/services-reference/enterprise/layer-table/). Geometry metadata reports `units=esriMeters`; this does not establish the business units of `f_area`/`tam_rai` or any separate Disaster Features area attributes. No unit conversion or reprojection was applied to project data.

For a scope check only, the reported 3857 extents were converted to approximate longitude/latitude using the Web Mercator inverse (radius 6,378,137 m):

| ArcGIS layer | Approximate metadata extent `[west, south, east, north]` | Contains project Ongkharak representative point? |
|---|---|---|
| 0 | `[99.420873, 17.733731, 100.554819, 18.823647]` | No |
| 1 | `[99.075054, 13.592667, 100.554819, 18.824112]` | No |

The project point is **101.010122, 14.097076**. This compares a point with reported metadata bounds; it does not prove coverage quality, legal geography, current flooding or absence of flooding. In particular these resources cannot be assumed to provide nationwide/current Ongkharak satellite observations. Layer 1 is explicitly labelled a flood-risk layer, which must remain distinct from a dated satellite flood observation. Empty metadata `copyrightText` is not an explicit display/redistribution license.

## Integration decisions

1. Keep the current Disaster Platform Features integration path and independently verified access state. The seven ArcGIS fields, service CRS and record limit must not be applied to the separate 29-property Features sample merely because both contain `f_area`.
2. Preserve the one-day Ongkharak empty result and separate nonempty 30-day sample with their actual query windows and response timestamps. No ArcGIS extent, STAC footprint or longer window becomes a substitute one-day flood mask.
3. Retain unknown acquisition, business units, scientific CRS/quality/coverage and resource-specific public-display rights. The supplied dictionary explicitly qualifies these and does not close them.
4. Before a production layer, obtain a provider reference for the actual `/features/flood/{window}` fields (including `f_area`, `h3_area`, `_area`, `rice_area` and time fields), plus permission/attribution/retention terms and bounded complete-retrieval semantics. The [updated saved questions](GISTDA_DISASTER_PRODUCT_QUESTIONS_TH.md) identify the exact service distinction; they remain unsent.

No production code, source credential, private diagnostic request, database content or public map layer changed during this document review. Existing source-specific disabled/unavailable states remain appropriate. Local ignored `artifacts/gistda-dictionary-review-2026-10-27/reconciliation.json` retains the value-free comparison, primary metadata hashes and source-file hashes. No new test suite was required for these documentation changes; the independent 14/14 primary-metadata reconciliation is the verification performed. Shutdown remains ineligible because the broader roadmap and these source acceptance inputs are incomplete.
