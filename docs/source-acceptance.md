# Source acceptance investigation — 2026-10-25

These are actual discovery/probe results. They do not mark a source integrated or authorize redistribution. No borrowed dashboard keys were used.

## RID — initial daily-storage acceptance completed 2026-10-26

[RID API documentation](https://app.rid.go.th/reservoir/api/document/dam) identifies `https://app.rid.go.th/reservoir/api/dam/public`. A read-only request returned HTTP 200, application/json, report date 2026-10-25, 35 declared and actual records, and 35 unique source IDs. Fields include capacity, storage, active/dead storage, volume, percent_storage, inflow and outflow. No coordinates are returned by that product.

The follow-up matched all 35 identities and published point coordinates from the official linked reservoir interface. The official RID catalog on data.go.th links to that same interface under DGA reuse terms. Capacity semantics and date-only precision are now explicit; inflow/outflow accumulation window and units remain unresolved and those fields are excluded. The initial daily-storage adapter, contracts, A/B publication, read API and layer are implemented and tested. See the [dated acceptance record](rid-acceptance-2026-10-26.md) for exact evidence, license-scope interpretation and limitations. Run 40287126263 published all 35 reports to Atlas, and the production API passed shared validation; no local capture is served in production.

## TMD — public CAP product accepted 2026-10-26

The official [RSS directory](https://www.tmd.go.th/service/rss) links the public Thai CAP feed, also listed in the WMO Register. No API key is required for this separate channel. The real feed and six linked Actual/Public CAP 1.2 documents were fetched successfully. Feed copyright declares public domain; the TMD copyright notice permits attributed non-commercial republication, matching the user's confirmed use. Registered forecast/radar products remain separate and unaccepted.

All six captured messages had expired before retrieval. The adapter preserves original classifications, CAP issue/effective/expiry times, exact update/cancel references, explicit province codes and all 481 polygon rings. It never turns a fresh retrieval of an old message into a current warning. The [dated acceptance record](tmd-cap-acceptance-2026-10-26.md) documents the permission interpretation, RSS/CAP timestamp discrepancy, conservative request policy, exclusions and tests. Run 40294693768 published all six messages to Atlas; the production API validated all records and correctly reported zero within validity. Weather/RID remained unchanged.

## HII / ThaiWater — a specification is not a live data entitlement

[ThaiWater.Standard](https://standard.thaiwater.net/docs/) documents exchange formats, agency-defined base URLs, authentication and station metadata. Its base URL examples use an illustrative agency domain, rather than offering one nationwide live endpoint. Authentication guidance describes issued static/dynamic API tokens. An authorized provider endpoint, credentials, coverage, station datum, terms and sample data are still required. Website-internal endpoints and third-party wrappers were not adopted as undocumented production APIs.

Follow-up on 26 October found a separate official [HII water-level archive catalog](https://data.hii.or.th/dataset/water-level) and [rain archive](https://data.hii.or.th/dataset/hii-rainfall). These specify attributed non-commercial reuse and monthly publication, with public no-key CSV downloads. The linked station metadata download contains 1,396 rows. The October 2026 water-level directory was empty; the September directory contained 399 CSVs including station metadata. A single real station sample, ATG011, contained 4,320 ten-minute rows for September, ending at the unqualified local-looking text `2026-09-30 23:50:00`. The catalog gives water-level units as meters relative to mean sea level and documents missing-value sentinels. Timezone, exact per-station datum/quality flags and current API entitlement are not yet accepted. No historical file was relabelled current, imported into production or used as a live fallback. Catalog availability narrows the access gap for archives; it does not supply a current water-status API. User instructions are in [HII/GISTDA setup](HII_GISTDA_SETUP_TH.md).

## GISTDA — Disaster Platform Features access found; scientific/permission acceptance open

The user supplied the [official Disaster Platform manual](https://disaster.gistda.or.th/manual_api.pdf) and successful Swagger screenshots. Read-only inspection of the live form confirms `/features/flood/1day` and optional `bbox`, `limit`, `offset`, `pv_idn`, `ap_idn`, `tb_idn`. The screenshot uses an `API-Key` header and shows HTTP 200 with zero matched/returned features. Its `timeStamp` is response time, not satellite acquisition time. A valid empty response does not establish complete coverage or no flooding. This is user-supplied access evidence; the rewritten Actions client still needs a fresh main run.

The [specific one-day Disaster Platform resource](https://opendata.gistda.or.th/th/dataset/flood-disaster-data/resource/062a08da-a6a9-4db7-9af7-1d345e38563a) explicitly says **License not specified**. Key configuration and a technical web-map manual do not settle redistribution/attribution terms, quota, actual acquisition/publication fields, geometry/CRS, units, empty-result/coverage semantics or quality. A real nonempty feature sample and those definitions remain necessary before public layer acceptance. No daily observations are fabricated from the product label or response time.

The current manual-only **Inspect GISTDA Disaster Features** workflow uses `GISTDA_API_KEY` solely in the header, requests one page of the explicitly selected product window, and defaults to the canonical Ongkharak administrative filter `ap_idn=2604`. Returned links are discarded because they can echo a key. Logs contain sanitized structure plus validated counts/response timestamp only. The user confirmed key replacement and GitHub secret update after the latest screenshot exposure; no screenshot key is copied, stored or reused. The workflow has no schedule, database credentials, retries, pagination or publication. See [current review](gistda-disaster-features-review-2026-10-26.md) and [Thai instructions](HII_GISTDA_SETUP_TH.md).

Earlier legacy point probes, v1.1/v1.0 at Bangkok and v1.1 at Ongkharak, returned HTTP 404. Their distinct [DGA catalog](https://data.go.th/dataset/disasters-03) identifies Open Data Common. That metadata is not transferred to the new Disaster Platform resource, and the legacy 404s are not attributed to the Features API. The [historical review](gistda-product-25-review-2026-10-26.md) and unsent legacy support draft are retained as evidence, not current run instructions. GISTDA remains unintegrated; no agency message or data publication has occurred.

## Gate result

| Source | Official reference found | Actual product sample | Remaining dependency |
|---|---|---|---|
| Open-Meteo | Yes | 1,005 validated point forecasts published to Atlas and read from production on 2026-10-26 | Non-commercial use confirmed; remaining live restart/failover qualification is operational |
| RID daily storage | Yes | 35 verified daily reports and matching published point coordinates | Published and verified on production; flows remain excluded pending definitions |
| TMD public CAP | Yes | Six verified Actual/Public CAP messages and official polygons | Published and verified on production; registered forecast/radar remain outside accepted scope |
| HII / ThaiWater | Exchange standard | No authorized live product sample | Agency endpoint/access agreement, datum and product acceptance |
| GISTDA | Yes | User screenshot: HTTP 200 empty Features response; no acquisition sample | New client workflow verification, specific reuse terms and acquisition/product acceptance |

These unresolved gates are concrete dependencies. Do not populate production layers with guessed coordinates, units, credentials or illustrative measurements.

## Basin geometry — authoritative product located, permission pending

The ONWR [22 basins under the Royal Decree catalog](https://gdcatalog.go.th/dataset/gdpublish-dataset-32-0113) links an official WGS84 shapefile archive, but its specific dataset license is **License not specified**. The separate water-chart and watershed-classification products have different scopes and terms; they cannot silently license this resource. No basin geometry was incorporated. The earlier 25-basin dataset is explicitly superseded and was not used as current 22-basin geometry.

## User access clarification

On 26 October the user clarified that neither HII nor GISTDA access had been registered. The GISTDA gateway was inspected read-only through its email sign-in and empty registration form. No personal fields, credentials, consent checkboxes or account submissions were entered. Product documentation and reuse permissions behind membership remain uninspected. The setup guide gives the verified registration path and a draft HII data request for the user to send; no message was sent to either agency.
