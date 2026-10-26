# GISTDA Disaster Platform Features — current access review

References reviewed 2026-10-26; Actions verification added 2026-10-27, Asia/Bangkok. This replaces the legacy point-route diagnostic as the current integration path; it does not grant product acceptance or public redistribution rights.

## Official references and observed response

- [Official API manual](https://disaster.gistda.or.th/manual_api.pdf), 15 pages. Local ignored reference: `artifacts/gistda-disaster-review/manual_api.pdf`, SHA-256 `b95e137c451a6e81f3d956f25591bc4c1fbcc6d17a0e5d8c74b798444cf4f4f9`. Relevant manual sections/pages and their figures were read and rendered. It describes OGC GeoJSON Features and WMS/WMTS/TMS, account/key creation and Swagger authorization. Technical map-use instructions do not by themselves settle the dataset's redistribution license.
- [Live Disaster API documentation](https://disaster.gistda.or.th/services/open-api), inspected read-only without entering a key. Server: `https://api-gateway.gistda.or.th/api/2.0/resources`. Documented flood Features products: `/features/flood/1day`, `/3days`, `/7days`, `/30days`. These are distinct windows, never automatic fallbacks.
- [Specific official one-day resource](https://opendata.gistda.or.th/th/dataset/flood-disaster-data/resource/062a08da-a6a9-4db7-9af7-1d345e38563a): **License not specified**. Do not transfer the separate legacy #25/DGA catalog's Open Data Common metadata to this Disaster Platform resource.
- The user's Swagger screenshots show a GET to `/features/flood/1day?limit=1&offset=0`, authentication in the **`API-Key` header**, HTTP 200, `type: FeatureCollection`, `features: []`, `numberMatched: 0`, `numberReturned: 0`, and `timeStamp: 2026-10-26T16:22:22.657Z`. This is user-supplied successful access evidence. Independent Actions verification followed as recorded below; neither response provides a satellite acquisition sample.

The live form documents optional `bbox` (xmin,ymin,[zmin],xmax,ymax,[zmax]), `limit`, nonnegative `offset`, `pv_idn`, `ap_idn`, and `tb_idn`. It does not use the legacy `lat`, `lon`, `area` fields. Canonical district **TH-D-2604 / Ongkharak** maps to `ap_idn=2604`; this is an administrative filter rather than a flood assertion or a representative-point query. No unverified bbox/geometry syntax is constructed.

## Bounded private diagnostic and versioned requests

`.github/workflows/gistda-access.yml` is now **Inspect GISTDA Disaster Features**. Use a fresh **Run workflow → main → window: 1day → ap_idn: 2604**. Clearing `ap_idn` reproduces an unfiltered service query; it still inspects only one page (`limit=1`, `offset=0`). The key is read solely from repository secret `GISTDA_API_KEY`; the user confirmed rotating the key and updating that secret after the screenshots. No screenshot credential is copied or used.

The same workflow also accepts a versioned request when `.github/gistda-inspection.json` changes on **main**. Other push paths and pull requests do not invoke this diagnostic. This avoids requiring a human Actions dispatch for each reviewed schema inspection. The fixed, size-bounded JSON file contains exactly `request_id`, `window`, `ap_idn`; it cannot provide an endpoint or credential. The allowlisted product/filter validation is the same. The current explicit request `2026-10-27-01` selects `30days` with a blank administrative filter for one schema-inspection page. It does not schedule polling or publication. The existing manual form remains available.

`scripts/probe_gistda_features.py` sends exactly one GET with an `API-Key` header to a fixed-host, allowlisted product window. It has no retries, redirects, pagination, database credentials, publication or schedule, and caps JSON at 2 MiB with bounded network time. The legacy probe remains only to reproduce historical evidence.

**Response `links[].href` can echo a key even when the request authenticates in a header.** All returned links are discarded before structural logging, never followed or written to artifacts. Only fixed classifications, bounded field/type structure and validated counts/response time are logged. Provider errors, including an error wrapped in HTTP 200, never become accepted empty observations. HTTP 404 is treated as an error, independently of the documentation's brief description.

A valid empty envelope reports `EMPTY_FEATURE_COLLECTION_OBSERVED`; a nonempty inspected page reports `FEATURE_PAGE_OBSERVED_SCHEMA_UNVERIFIED`. Both are access-diagnostic outcomes only. The reported `complete_collection` compares returned features with the service's own matched count for that query; it does not certify national coverage, satellite coverage or detection quality. `timeStamp` remains an API response timestamp, never an acquisition time. Zero features never means all-clear, no floodwater, or no observation gaps.

## Independent one-day access verification — 2026-10-27

The user started fresh run [40364997446](https://github.com/tordave1150/hazard-intelligence/actions/runs/40364997446) on `9659197f190354598a0095fb25df0cd2b8cade91`, job 121720182777. Every step succeeded. Its workflow window was **27 October 2026 00:03:18–00:03:36 ICT** (26 October 17:03:18–17:03:36 UTC), not a satellite acquisition period. Whitelisted input lines confirm `window=1day`, `ap_idn=2604`; no secret value was retrieved or printed.

The single header-authenticated request returned HTTP 200, `EMPTY_FEATURE_COLLECTION_OBSERVED`, `numberMatched=0`, `numberReturned=0`. The response timestamp was `2026-10-26T17:03:33.525Z` / **27 October 00:03:33.525 ICT**. Two returned links were discarded before logging. Only the empty features array, numeric count types, timestamp type and FeatureCollection type structure were recorded. This completes verification of this client/request combination, not scientific product acceptance, national coverage or a no-flood finding. Acquisition time remains UNVERIFIED.

The same code passed CI [40362226402](https://github.com/tordave1150/hazard-intelligence/actions/runs/40362226402), including Python, TypeScript, 14 frontend tests and the production build; Vercel deployed successfully and the updated source registry was inspected on production. No source data was written to Atlas.

## Remaining integration work

1. Obtain a nonempty schema sample: the versioned request `2026-10-27-01` explicitly selects `window=30days`, blank `ap_idn`, limit=1 to inspect the documented broader service window. Its result is pending; it is not an automatic fallback or an accepted one-day observation. No extra human dispatch is required for that reviewed main push.
2. Confirm the specific Disaster Platform resource's public display/redistribution terms, attribution, quota, coverage and empty-result semantics. A [current Thai question draft](GISTDA_DISASTER_PRODUCT_QUESTIONS_TH.md) is prepared for the catalog's `disaster@gistda.or.th` contact and remains unsent. The previous unsent legacy-route support draft is historical, not the current next step.
3. Obtain a real nonempty feature sample and official meanings for acquisition/publication fields, CRS, geometry, units and quality. The current manual/form do not establish all of these. A longer documented window, if explicitly selected, remains labelled with that window and cannot masquerade as one-day observations.
4. Implement bounded complete retrieval, source-specific contracts, persistence/retention, API/map behavior and failure tests only after those inputs are accepted.

No GISTDA data has been published to Atlas, no flood layer has been enabled, and no agency message has been sent. The [legacy route review](gistda-product-25-review-2026-10-26.md) preserves the three prior 404 experiments without attributing those failures to the new Features API.
