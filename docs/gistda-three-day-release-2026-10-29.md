# GISTDA three-day product and Actions cleanup — 29 October 2026

The map now targets the provider's retrospective **3days / ย้อนหลัง 3 วัน** product. The user requested this change after verified unfiltered national queries returned 0 features for 1day, 7,846 for 3days, 78,958 for 7days and 164,821 for 30days. Those inspections were count/sample checks; the complete new publication is verified separately below. Acquisition time remains unknown and is never inferred from the window or retrieval clock.

## Complete retrieval, bounded delivery

- Product/control/status key: `gistda:flood_3days_thailand`; collection: `satellite_flood_3days_latest`.
- Provider requests: fixed HTTPS host, `API-Key` header, no administrative filter, 100 results/page, at most 200 pages / 20,000 features, 64 MiB cumulative provider bytes, 2,000,000 coordinate positions and a 600-second collection deadline. Existing per-feature topology/coordinate/complexity and administrative checks still apply. Count changes, duplicate/repeated results, invalid geometry and incomplete pages prevent publication.
- Only checked geometry, generated feature IDs, canonical administrative references and fixed query metadata enter storage. Provider properties/IDs/links and unverified area/exposure values are discarded. No geometry repair or simplification is applied.
- Complete normalized feed budget: 32 MiB. Documents contain at most 100 features and at most 1 MiB including metadata. A/B slots keep at most two generations and 512 documents per slot. A unique `(source_id, product_id, slot, chunk_id)` index prevents duplicate chunk identities. Validation checks the full contiguous chunk set, shared metadata, unique feature identities and complete count before the atomic pointer switch. Rollback restores feature/chunk accounting atomically as well as the generation pointer.
- `/api/flood-products` returns one bounded page. Follow `pagination.next_chunk` with `chunk` and the returned `generation`. A changed generation fails instead of mixing snapshots. `area_id` still filters supplied administrative codes; the client loads the complete national generation before rendering and then filters locally. A page is labelled `PARTIAL_RESULT` until assembly; its zero selected-area count is not a completed empty query.
- Browser assembly loads at most four pages concurrently and checks generation, metadata, ordered cursors, duplicate IDs and final record count. A failed refresh keeps the last completely assembled product with downgraded freshness. An unchanged generation requires only a health/metadata poll; the browser does not redownload all geometry every five minutes. The evidence list initially renders 100 buttons, with more available on demand; all loaded footprints remain on the map.
- The displayed source, methodology, map labels and tooltips say 3 days. The reader does not substitute the historical one-day national/pilot products. Their separately stored snapshots remain available for historical audit/rollback rather than being relabelled.

## Workflows kept and removed

Current workflows: application checks; latest daily weather; today's hourly weather; RID; TMD CAP; **Latest GISTDA Thailand 3-day flood product**; **Inspect GISTDA Disaster Features** (manual, defaults to 3days/national).

Removed `.github/workflows/gistda-candidate.yml` and its obsolete candidate request file: the fixed one-day Ongkharak candidate check is superseded by the national publisher and current manual inspector. Removed the one-day cadence-recording step from the publisher; it targeted the old product and is unnecessary for the new publication. The proposed extra availability workflow was never published and has been discarded to avoid duplicating the current inspector. Historical run logs and source-data snapshots are preserved.

The publisher keeps its daily 09:27 ICT target and uses the existing repository secrets. A reviewed push request uses `operation=publish_thailand_3days`. Manual command:

```powershell
python -m pipelines.gistda.run --publish --three-day
python -m scripts.mongo_admin verify
python -m scripts.mongo_admin rollback --source gistda
```

`--source gistda_1day` and `gistda_pilot` refer explicitly to the retained historical products. No visitor request invokes GISTDA ingestion.

## Validation

Local Python: **250 passed, 19 opt-in HTTP checks skipped**. Frontend: **43 passed**, including bounded concurrent loading; TypeScript and production build passed. Against the local server, **19 HTTP checks passed**, including three-page assembly, scope filtering and invalid cursor rejection. Existing schema definitions are unchanged, and the contract generator is reproducible including the earlier hourly contract.

Local browser QA used 205 explicitly synthetic footprints across three API pages. It displayed the complete total, “ย้อนหลัง 3 วัน”, LOCAL QA provenance, a bounded evidence list, and the same overlay selection in 2D/3D. Browser warning/error logs were empty. Synthetic checks do not establish provider data quality or device-wide performance.

[Production publication 40893469102](https://github.com/tordave1150/hazard-intelligence/actions/runs/40893469102) on `3fb43e4` succeeded: **7,846 features, all 79 provider pages, 79 stored documents**, unfiltered Thailand query, `observed_at=null`. Database audits before and after publication passed. [CI 40893469150](https://github.com/tordave1150/hazard-intelligence/actions/runs/40893469150) and [bounded-loading follow-up CI 40894976198](https://github.com/tordave1150/hazard-intelligence/actions/runs/40894976198) passed Python and web checks; both commits received successful Vercel deployment statuses.

Public production API readback fetched every page from generation `c49fe6c4-def7-4162-9684-45d0d043c83a`, confirmed **7,846 unique IDs**, equal feed metadata, null raw properties and canonical administrative references. The largest HTTP page was **257,891 bytes**; the complete paged responses totalled 15,919,675 bytes. This verifies bounded delivery without a single oversized national response. The seven supplied province references describe this query's returned data, not verified nationwide satellite coverage. Seven additional production HTTP checks passed for source metadata, methodology and invalid queries/cursors.

Production browser verification displayed **7,846** national footprints, “ย้อนหลัง 3 วัน”, and **3,595** when selecting Prachin Buri, matching the independently assembled API count. The overlay remained available in 2D/3D and browser warning/error logs were empty. A local screenshot is retained at ignored `artifacts/gistda-three-day-production.png`; count-only API evidence is at ignored `artifacts/gistda-three-day-production-receipt.json`. GitHub's workflow inventory confirmed exactly **seven active workflows**, with the obsolete candidate workflow absent.

Product reuse terms, actual acquisition dates, scientific coverage and unverified business metrics retain their existing qualifications.
