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

## GISTDA — official flood catalog, registration and unspecified license

The [official flood disaster dataset](https://opendata.gistda.or.th/th/dataset/flood-disaster-data) lists STAC and map services and directs users to register for a key at the GISTDA gateway. Its license metadata says **License not specified**. No other application's exposed key was reused. A user-owned authorized key, product reuse permission, real acquisition-time sample, coverage and tile metadata verification remain required. Satellite acquisition time must remain distinct from fetch time.

## Gate result

| Source | Official reference found | Actual product sample | Remaining dependency |
|---|---|---|---|
| Open-Meteo | Yes | 1,005 validated point forecasts published to Atlas and read from production on 2026-10-26 | Non-commercial use confirmed; remaining live restart/failover qualification is operational |
| RID daily storage | Yes | 35 verified daily reports and matching published point coordinates | Published and verified on production; flows remain excluded pending definitions |
| TMD public CAP | Yes | Six verified Actual/Public CAP messages and official polygons | Published and verified on production; registered forecast/radar remain outside accepted scope |
| HII / ThaiWater | Exchange standard | No authorized live product sample | Agency endpoint/access agreement, datum and product acceptance |
| GISTDA | Yes | No authenticated acquisition sample | Key, reuse license and acquisition/product acceptance |

These unresolved gates are concrete dependencies. Do not populate production layers with guessed coordinates, units, credentials or illustrative measurements.
