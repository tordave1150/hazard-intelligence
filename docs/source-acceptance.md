# Source acceptance investigation — 2026-10-25

These are actual discovery/probe results. They do not mark a source integrated or authorize redistribution. No borrowed dashboard keys were used.

## RID — documented endpoint responds, acceptance incomplete

[RID API documentation](https://app.rid.go.th/reservoir/api/document/dam) identifies `https://app.rid.go.th/reservoir/api/dam/public`. A read-only request returned HTTP 200, application/json, report date 2026-10-25, 35 declared and actual records, and 35 unique source IDs. Fields include capacity, storage, active/dead storage, volume, percent_storage, inflow and outflow. No coordinates are returned by that product.

The documentation describes volumes in million cubic meters and storage percentage, but does not explicitly resolve the inflow/outflow accumulation window or units. Redistribution/commercial permission, station coordinate metadata and reporting-time semantics remain unverified. A successful request alone cannot pass those gates, so no dam measurements are rendered yet. Next action: obtain permitted coordinate metadata, explicit flow definitions and reuse terms; then implement and test normalization/publication.

## TMD — official registration path found

The [official TMD API portal](https://data.tmd.go.th/api/) responded HTTP 200 to a direct read-only request. Its navigation points to registration for observation/forecast APIs at `http://data.tmd.go.th/api/registerPre.php`, and a separate NWP registration path. No account, agreement or credential was created or accepted. A registered product sample, reuse terms and per-product time/unit verification remain necessary before enabling warnings, radar or forecast products.

## HII / ThaiWater — a specification is not a live data entitlement

[ThaiWater.Standard](https://standard.thaiwater.net/docs/) documents exchange formats, agency-defined base URLs, authentication and station metadata. Its base URL examples use an illustrative agency domain, rather than offering one nationwide live endpoint. Authentication guidance describes issued static/dynamic API tokens. An authorized provider endpoint, credentials, coverage, station datum, terms and sample data are still required. Website-internal endpoints and third-party wrappers were not adopted as undocumented production APIs.

## GISTDA — official flood catalog, registration and unspecified license

The [official flood disaster dataset](https://opendata.gistda.or.th/th/dataset/flood-disaster-data) lists STAC and map services and directs users to register for a key at the GISTDA gateway. Its license metadata says **License not specified**. No other application's exposed key was reused. A user-owned authorized key, product reuse permission, real acquisition-time sample, coverage and tile metadata verification remain required. Satellite acquisition time must remain distinct from fetch time.

## Gate result

| Source | Official reference found | Actual product sample | Remaining dependency |
|---|---|---|---|
| Open-Meteo | Yes | 1,005 validated point forecasts published to Atlas and read from production on 2026-10-26 | Non-commercial use confirmed; remaining live restart/failover qualification is operational |
| RID | Yes | 35 dam records, read-only probe | Coordinates, flow/time definitions, reuse terms and adapter tests |
| TMD | Yes | No authenticated product sample | Registered access, terms and product acceptance |
| HII / ThaiWater | Exchange standard | No authorized live product sample | Agency endpoint/access agreement, datum and product acceptance |
| GISTDA | Yes | No authenticated acquisition sample | Key, reuse license and acquisition/product acceptance |

These unresolved gates are concrete dependencies. Do not populate production layers with guessed coordinates, units, credentials or illustrative measurements.
