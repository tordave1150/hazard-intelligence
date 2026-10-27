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

The same workflow also accepts a versioned request when `.github/gistda-inspection.json` changes on **main**. Other push paths and pull requests do not invoke this diagnostic. This avoids requiring a human Actions dispatch for each reviewed schema inspection. The fixed, size-bounded JSON file requires `request_id`, `window`, `ap_idn` and permits only optional `service` (`features` or `stac`); it cannot provide an endpoint or credential. The allowlisted product/filter validation is the same. Requests 2026-10-27-01/02 explicitly selected the separate 30days Features service with a blank administrative filter; current request 2026-10-27-03 explicitly selects the one-day STAC item metadata. It does not schedule polling or publication. The existing manual form remains available.

`scripts/probe_gistda_features.py` sends exactly one GET with an `API-Key` header to a fixed-host, allowlisted product window. It has no retries, redirects, pagination, database credentials, publication or schedule, and caps JSON at 2 MiB with bounded network time. The legacy probe remains only to reproduce historical evidence.

**Response `links[].href` can echo a key even when the request authenticates in a header.** All returned links are discarded before structural logging, never followed or written to artifacts. Only fixed classifications, bounded field/type structure and validated counts/response time are logged. Provider errors, including an error wrapped in HTTP 200, never become accepted empty observations. HTTP 404 is treated as an error, independently of the documentation's brief description.

A valid empty envelope reports `EMPTY_FEATURE_COLLECTION_OBSERVED`; a nonempty inspected page reports `FEATURE_PAGE_OBSERVED_SCHEMA_UNVERIFIED`. Both are access-diagnostic outcomes only. The reported `complete_collection` compares returned features with the service's own matched count for that query; it does not certify national coverage, satellite coverage or detection quality. `timeStamp` remains an API response timestamp, never an acquisition time. Zero features never means all-clear, no floodwater, or no observation gaps.

## Independent one-day access verification — 2026-10-27

The user started fresh run [40364997446](https://github.com/tordave1150/hazard-intelligence/actions/runs/40364997446) on `9659197f190354598a0095fb25df0cd2b8cade91`, job 121720182777. Every step succeeded. Its workflow window was **27 October 2026 00:03:18–00:03:36 ICT** (26 October 17:03:18–17:03:36 UTC), not a satellite acquisition period. Whitelisted input lines confirm `window=1day`, `ap_idn=2604`; no secret value was retrieved or printed.

The single header-authenticated request returned HTTP 200, `EMPTY_FEATURE_COLLECTION_OBSERVED`, `numberMatched=0`, `numberReturned=0`. The response timestamp was `2026-10-26T17:03:33.525Z` / **27 October 00:03:33.525 ICT**. Two returned links were discarded before logging. Only the empty features array, numeric count types, timestamp type and FeatureCollection type structure were recorded. This completes verification of this client/request combination, not scientific product acceptance, national coverage or a no-flood finding. Acquisition time remains UNVERIFIED.

The same code passed CI [40362226402](https://github.com/tordave1150/hazard-intelligence/actions/runs/40362226402), including Python, TypeScript, 14 frontend tests and the production build; Vercel deployed successfully and the updated source registry was inspected on production. No source data was written to Atlas.

## Nonempty 30-day Features sample — 2026-10-27

Reviewed request 2026-10-27-01 ran successfully as [40371542079](https://github.com/tordave1150/hazard-intelligence/actions/runs/40371542079) on `a5a7e25`, job 121743295817. It selected 30days, blank ap_idn and limit=1/offset=0, returned HTTP 200 and **one inspected feature of 184,323 reported matches**. Response time was `2026-10-26T17:45:25.595Z` / 27 October 00:45:25.595 ICT. The source reported three links, all discarded; no links/assets were followed and no database was written. This single row is not a complete snapshot or an accepted one-day observation.

Its properties contained 29 fields, while the initial diagnostic exposed only the first 24 names/types. The field-name cap was explicitly raised to 48 for this client only (legacy remains 24), retaining value/key redaction. Reviewed request 2026-10-27-02 ran as [40372062673](https://github.com/tordave1150/hazard-intelligence/actions/runs/40372062673) on `d327f24`, job 121745098439, and returned the same reported counts at response time `2026-10-26T17:48:36.818Z` / 27 October 00:48:36.818 ICT. All 29 names/types were inspected:

`_area`, `_createdAt`, `_createdBy`, `_id`, `_updatedAt`, `_updatedBy`, `ap_en`, `ap_idn`, `ap_tn`, `building`, `f_area`, `file_name`, `h3_address`, `h3_area`, `hospital`, `length_road`, `mongo_id`, `objectid`, `population`, `pv_en`, `pv_idn`, `pv_tn`, `re_royin`, `re_royin_2`, `rice_area`, `school`, `tb_en`, `tb_idn`, `tb_tn`.

No field is yet documented as satellite acquisition time. `_createdAt`/`_updatedAt` cannot be relabelled acquisition, and no date is inferred from file_name. Area-like field names do not establish units or usable flood area; exposure-like fields do not establish current impact counts. Geometry was observed only as structure, not accepted coordinates/CRS. No values, geometry, creator identifiers, URLs or credentials were logged. CI 40371541983 and 40372062694 passed the associated Python/web checks and builds; Vercel succeeded.

## Documented STAC metadata inspection

The official flood catalog directly links four STAC items under `https://api-gateway.gistda.or.th/api/2.0/resources/stac/flood/collections/`:

| Window | Documented item path below collections |
|---|---|
| 1day | flood1day_r2/items/items_flood1day_r2 |
| 3days | flood3days_r2/items/items_flood3days_r2 |
| 7days | flood7days_r2/items/items_flood7days_r2 |
| 30days | flood30days_r2/items/items_flood30days_r2 |

The separate [30-day STAC resource](https://opendata.gistda.or.th/th/dataset/flood-disaster-data/resource/0ac1cd41-a388-4f8b-9bbc-0a518214d081) was read directly with HTTP 200 and also says License not specified. These paths come from published catalog links, not endpoint guessing. Request 2026-10-27-03 explicitly selects **service=stac, window=1day, ap_idn blank**. The same bounded HTTP client makes one GET to that fixed item, tests header compatibility, discards links/assets and never downloads raster assets. This does not fall back from a failed Features query or substitute an older product.

STAC output permits only validated UTC datetime/start_datetime/end_datetime metadata alongside bounded structure. Per the [primary STAC Item specification](https://github.com/radiantearth/stac-spec/blob/master/item-spec/item-spec.md), item datetime can be a nominal/representative time for combined assets; it is not automatically per-pixel or per-feature acquisition time. The diagnostic preserves that distinction and never accepts acquisition semantics from the field name alone. Reviewed request 2026-10-27-03 ran successfully as [40373514042](https://github.com/tordave1150/hazard-intelligence/actions/runs/40373514042) on `2cef32b94d4c0cad39065c0c1c3111d9fa6a4de7`, job 121750258758. The one-day STAC item returned HTTP 200, STAC version 1.0.0, with item `datetime=2026-10-26T00:10:00Z` (**26 October 2026 07:10 ICT**), no start/end interval and no accepted per-feature acquisition time. Four links were discarded and two assets were counted without reading names/URLs or downloading them. Geometry/bbox were inspected as structure only, never used as flood extent. The result remains STAC_ITEM_OBSERVED_SCHEMA_UNVERIFIED with acquisition_time_status UNVERIFIED. The item's geometry/asset footprint is not an accepted observed flood mask.

This completes the reviewed access/metadata inspections; no further probe is scheduled. A later push of documentation or other paths does not repeat these requests. Full offline verification passed **115 Python tests**, with 18 running-server HTTP checks skipped; diagnostic-only verification passed 38 tests. These tests validate the client and redaction behavior, not the provider's scientific meanings.

## Remaining integration work

Technical work resumed at the user's request on 27 October. The new [geometry/identity readiness inspection](gistda-geometry-readiness-2026-10-27.md) extends the same one-page diagnostic with value-free syntax/topology and pinned-code consistency checks. Request 2026-10-27-04 explicitly selects a separate 30days sample. These checks do not confer public-display permission or verified acquisition/coverage semantics; the provider question draft remains unsent.

1. Obtain the provider's definition of the verified one-day STAC item time and its relation to Features rows/assets. Keep nominal/search time, retrieval time and any actual acquisition time distinct; retain one-day and 30-day products separately.
2. Confirm the specific Disaster Platform resource's public display/redistribution terms, attribution, quota, coverage and empty-result semantics. A [current Thai question draft](GISTDA_DISASTER_PRODUCT_QUESTIONS_TH.md) is prepared for the catalog's `disaster@gistda.or.th` contact and remains unsent. The previous unsent legacy-route support draft is historical, not the current next step.
3. Obtain a real nonempty feature sample and official meanings for acquisition/publication fields, CRS, geometry, units and quality. The current manual/form do not establish all of these. A longer documented window, if explicitly selected, remains labelled with that window and cannot masquerade as one-day observations.
4. Implement bounded complete retrieval, source-specific contracts, persistence/retention, API/map behavior and failure tests only after those inputs are accepted.

No GISTDA data has been published to Atlas, no flood layer has been enabled, and no agency message has been sent. The [legacy route review](gistda-product-25-review-2026-10-26.md) preserves the three prior 404 experiments without attributing those failures to the new Features API.
