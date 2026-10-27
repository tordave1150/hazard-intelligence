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

Connected publication/deployment evidence will be added after the reader is deployed and the reviewed national request completes. The full roadmap and conditional PC shutdown remain incomplete.
