# GISTDA Disaster Platform Features — current access review

Reviewed 2026-10-26, Asia/Bangkok. This replaces the legacy point-route diagnostic as the current integration path; it does not grant product acceptance or public redistribution rights.

## Official references and observed response

- [Official API manual](https://disaster.gistda.or.th/manual_api.pdf), 15 pages. Local ignored reference: `artifacts/gistda-disaster-review/manual_api.pdf`, SHA-256 `b95e137c451a6e81f3d956f25591bc4c1fbcc6d17a0e5d8c74b798444cf4f4f9`. Relevant manual sections/pages and their figures were read and rendered. It describes OGC GeoJSON Features and WMS/WMTS/TMS, account/key creation and Swagger authorization. Technical map-use instructions do not by themselves settle the dataset's redistribution license.
- [Live Disaster API documentation](https://disaster.gistda.or.th/services/open-api), inspected read-only without entering a key. Server: `https://api-gateway.gistda.or.th/api/2.0/resources`. Documented flood Features products: `/features/flood/1day`, `/3days`, `/7days`, `/30days`. These are distinct windows, never automatic fallbacks.
- [Specific official one-day resource](https://opendata.gistda.or.th/th/dataset/flood-disaster-data/resource/062a08da-a6a9-4db7-9af7-1d345e38563a): **License not specified**. Do not transfer the separate legacy #25/DGA catalog's Open Data Common metadata to this Disaster Platform resource.
- The user's Swagger screenshots show a GET to `/features/flood/1day?limit=1&offset=0`, authentication in the **`API-Key` header**, HTTP 200, `type: FeatureCollection`, `features: []`, `numberMatched: 0`, `numberReturned: 0`, and `timeStamp: 2026-10-26T16:22:22.657Z`. This is user-supplied successful access evidence, not yet an independently verified Actions result or a satellite acquisition sample.

The live form documents optional `bbox` (xmin,ymin,[zmin],xmax,ymax,[zmax]), `limit`, nonnegative `offset`, `pv_idn`, `ap_idn`, and `tb_idn`. It does not use the legacy `lat`, `lon`, `area` fields. Canonical district **TH-D-2604 / Ongkharak** maps to `ap_idn=2604`; this is an administrative filter rather than a flood assertion or a representative-point query. No unverified bbox/geometry syntax is constructed.

## Bounded private diagnostic

`.github/workflows/gistda-access.yml` is now **Inspect GISTDA Disaster Features**. Use a fresh **Run workflow → main → window: 1day → ap_idn: 2604**. Clearing `ap_idn` reproduces an unfiltered service query; it still inspects only one page (`limit=1`, `offset=0`). The key is read solely from repository secret `GISTDA_API_KEY`; the user confirmed rotating the key and updating that secret after the screenshots. No screenshot credential is copied or used.

`scripts/probe_gistda_features.py` sends exactly one GET with an `API-Key` header to a fixed-host, allowlisted product window. It has no retries, redirects, pagination, database credentials, publication or schedule, and caps JSON at 2 MiB with bounded network time. The legacy probe remains only to reproduce historical evidence.

**Response `links[].href` can echo a key even when the request authenticates in a header.** All returned links are discarded before structural logging, never followed or written to artifacts. Only fixed classifications, bounded field/type structure and validated counts/response time are logged. Provider errors, including an error wrapped in HTTP 200, never become accepted empty observations. HTTP 404 is treated as an error, independently of the documentation's brief description.

A valid empty envelope reports `EMPTY_FEATURE_COLLECTION_OBSERVED`; a nonempty inspected page reports `FEATURE_PAGE_OBSERVED_SCHEMA_UNVERIFIED`. Both are access-diagnostic outcomes only. The reported `complete_collection` compares returned features with the service's own matched count for that query; it does not certify national coverage, satellite coverage or detection quality. `timeStamp` remains an API response timestamp, never an acquisition time. Zero features never means all-clear, no floodwater, or no observation gaps.

## Remaining integration work

1. Verify the new client through a fresh main Actions run using the privately configured secret.
2. Confirm the specific Disaster Platform resource's public display/redistribution terms, attribution, quota, coverage and empty-result semantics. The previous unsent legacy-route support draft is historical, not the current next step.
3. Obtain a real nonempty feature sample and official meanings for acquisition/publication fields, CRS, geometry, units and quality. The current manual/form do not establish all of these. A longer documented window, if explicitly selected, remains labelled with that window and cannot masquerade as one-day observations.
4. Implement bounded complete retrieval, source-specific contracts, persistence/retention, API/map behavior and failure tests only after those inputs are accepted.

No GISTDA data has been published to Atlas, no flood layer has been enabled, and no agency message has been sent. The [legacy route review](gistda-product-25-review-2026-10-26.md) preserves the three prior 404 experiments without attributing those failures to the new Features API.
