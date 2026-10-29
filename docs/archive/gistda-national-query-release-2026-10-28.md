> HISTORICAL RECORD — Superseded. Use [current scope](../current-scope.md). Sample locations and retired commands here are not user preferences or current run instructions.

# GISTDA nationwide daily query — 28 October 2026

The Ongkharak-only view was an application pilot restriction (`ap_idn=2604`), not a provider restriction. The active implementation now supports an unfiltered Features `1day` query and local administrative filtering for Thailand, regions, provinces and districts. This does not assert nationwide satellite acquisition coverage.

## The bbox example

The user's bboxfinder URL `#13.645987,100.408173,13.840080,100.661545` describes a Bangkok rectangle. For the API's x-min,y-min,x-max,y-max syntax, use `bbox=100.408173,13.645987,100.661545,13.840080`. It is an optional search filter, not a prescribed national service boundary. Do not copy the URL fragment's latitude-first order into the API. The national ingestion intentionally sends neither this example bbox nor an administrative filter.

## Provider evidence

Reviewed request `2026-10-28-01`, commit `a2cdba9`, run [40547286159](https://github.com/tordave1150/hazard-intelligence/actions/runs/40547286159), job 122341173769: the unfiltered `1day` endpoint returned HTTP 200, numberMatched=0 and numberReturned=0 at **2026-10-28 00:05:55.498 ICT** (2026-10-27T17:05:55.498Z). This is a complete empty query response, not proof of no flooding. No alternate product window was substituted.

## Data flow and bounds

GitHub Actions existing secret → fixed-host `API-Key` header → bounded collector → `GistdaNationalFloodFeed` → Atlas A/B pointer → read API → selected-area filter → the existing 2D/3D overlay.

- Product: `flood_1day_thailand`, scope `TH`; collection `satellite_flood_national_latest`, at most two envelopes, each at most 4 MiB in JSON and BSON.
- Fixed page size 100; at most 10 requests, 1,000 features, 100,000 total positions, 4 MiB cumulative provider body and 120 seconds. Existing per-feature topology/ring limits still apply. This is intentionally a bounded small-vector path, not storage for large scenes. Larger products fail with a clear budget reason and retain the last complete product; tiles/static hosting remain the scaling path.
- Offset advances by actual returned count. Matched counts must remain stable; repeated geometry/administrative fingerprints, premature empty pages, incomplete totals, invalid codes/geometries, HTTP failures and exceeded bounds prevent promotion.
- `response_at` is the earliest validated page response time, `fetched_at` is final retrieval. The provider supplies no version token: count/duplicate checks do not prove an atomic upstream snapshot. This qualification is stored and displayed.
- Persist only checked geometry, generated internal IDs and canonical province/district references. Provider links, feature IDs, other properties, unverified exposure/area values and keys are discarded.
- Administrative membership uses the provider codes checked against the pinned directory. No exact polygon clipping or spatial coverage claim follows from those codes.
- Acquisition remains null/UNKNOWN. A fresh query is not a fresh satellite observation. Empty results are not safe/all-clear conditions.

## Compatibility and operation

The reader prefers the national product. Before its first publication it can still read the old pilot with explicit pilot labels and scope. A malformed national product is unavailable rather than silently falling back. The old pilot collection/pointer is preserved and audited separately; no destructive migration is required.

`gistda.yml` is now **Latest GISTDA Thailand flood product**. It runs `python -m pipelines.gistda.run --publish --national`, using existing secrets. Daily target remains 09:27 ICT; actual timestamps govern freshness. A reviewed request must explicitly say `operation=publish_thailand_1day`. Main manual dispatch is also supported. `python -m scripts.mongo_admin rollback --source gistda` addresses the national A/B slots; `--source gistda_pilot` addresses the preserved pilot.

API examples: `/api/flood-products?area_id=TH`, `TH-P-10`, `TH-D-1001`, `TH-D-2604` and `TH-D-5709`. For the national product these are all supported query scopes; each returns only matching canonical administrative records. `feed.record_count` describes all provider results; `records.length` describes the selected area. UNKNOWN acquisition and EMPTY_RESULT/UNAVAILABLE remain separate.

## Validation before publication

210 offline Python tests passed (19 HTTP checks skipped offline); 20 frontend tests, TypeScript and production build passed. Tests exercise pagination, changed totals, repeats, limits, identity hierarchy, independent pilot/national storage, rollback and area filtering beyond Ongkharak. Synthetic fixture files are explicitly test-only and are never sent to Atlas.

## Connected publication and verification

Reader/collector commit `08033aa` passed CI [40548494310](https://github.com/tordave1150/hazard-intelligence/actions/runs/40548494310) and Vercel before the writer request. The existing pilot remained readable during this transition.

Reviewed publication commit `4194c29`, [run 40548798337](https://github.com/tordave1150/hazard-intelligence/actions/runs/40548798337), job 122346589963 succeeded. The actual national provider response was **2026-10-28 00:15:40.934 ICT**, retrieved at 00:15:41.031542 ICT; zero matched/returned features, one complete page, unknown acquisition. Atlas audit verified all five product pointers (including preserved pilot) and unique indexes: weather 1005 active/2010 stored, RID 35/70, TMD 1/2 envelopes, pilot 1/1, national 1/1, with two-envelope limits for each GISTDA collection.

- All 19 production HTTP tests passed. Additional real API checks verified `in_scope=true`, storage=mongo, no error, UNKNOWN acquisition and EMPTY_RESULT for Thailand, Central, Bangkok, Phra Nakhon, Ongkharak and Mae Sai. The national feed is preferred over the pilot.
- Production browser: both TMD and GISTDA enabled together; current orange TMD frames remain visible in national view. The GISTDA panel says Thailand query, zero actual results, 00:15 retrieval and acquisition unknown. Bangkok selection remains supported and does not display an out-of-pilot error. Console warnings/errors: none.
- Local explicitly synthetic national fixture: nonempty footprint visible in both 2D and native 3D; selection works; changing to Mae Sai removes unrelated footprints and reports a supported empty result. No synthetic data entered Atlas.
- Mobile browser viewport 390×844: Bangkok GISTDA panel opens/closes through Area; root clientWidth and scrollWidth both 375, with no horizontal page overflow. This is browser responsive verification, not a physical-device/GPU benchmark.
- The owned preview process exited cleanly, port 3002 was released, the hash-checked temporary fixture was removed, all owned browser tabs were closed and viewport was restored. Original attached files were unchanged.

Ignored local evidence: `artifacts/gistda-national-publication-2026-10-28.json`, `gistda-national-production-api-2026-10-28.json`, `gistda-national-http-2026-10-28.xml`, `gistda-national-production-2026-10-28.png`, `gistda-national-bangkok-production-2026-10-28.png`, `gistda-national-mobile-production-2026-10-28.png`, and the synthetic `gistda-local-qa/national-nonempty-{2d,3d}.png` captures.

Remaining limits: larger vector products exceed the explicit budget and require the separate tile/static-hosting path; true acquisition time, full satellite coverage and exact administrative clipping remain unverified. The full roadmap and conditional PC shutdown remain incomplete (HII, basins, platform rollback/access and physical-device/GPU checks are still open).
