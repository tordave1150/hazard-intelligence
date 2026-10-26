# Source registry

Machine-readable registry: `apps/web/data/source-registry.json`. It records endpoint/product reference, source category, authentication, licence, commercial and redistribution permission, quota, cadence/latency, coverage/resolution, units/CRS, fallback and terms-review date. `/sources` presents it; the map separately presents actual data age.

| Source | Evidence at 2026-10-26 | Release state |
|---|---|---|
| Open-Meteo daily forecast | Production run 40257438014 published and served 1,005/1,005 validated points, four daily periods, FRESH/SUCCESS on 2026-10-26; user confirmed non-commercial use | Connected on production; source attribution retained |
| RID daily dam storage | Documented GET, 35 matched identities and official published coordinates, date-only precision, capacities/percent semantics and linked DGA catalog reuse reviewed | Connected on production: run 40287126263 published 35/35 reports; unique indexes and retention verified. Flows remain excluded |
| TMD public CAP | Official public RSS and linked CAP documents, public-domain feed declaration and attributed non-commercial reuse reviewed; six real expired messages verified | Connected on production: run 40294693768 published six CAP messages, all expired by retrieval. Registered radar/forecast remain separate |
| HII / ThaiWater gauges | Official public monthly archives, CC BY-NC catalog, 1,396 metadata rows and one real September station sample inspected; October directory empty | Live layer planned/disabled; current API, datum/timezone/quality and product acceptance pending |
| GISTDA flood products | Selected #25 one-day catalog directly identifies Open Data Common; user-owned backend secret configured, but manual v1.1 and v1.0 point requests both returned 404 | Unavailable/disabled pending current endpoint/parameter/entitlement confirmation and acquisition-time sample; support request drafted, not sent |
| Administrative boundaries | Pinned attributed geometry plus official downloadable DOPA code/name comparison: 77 provinces/928 districts; one code and six Thai names corrected | Directory reference is 2023-09-01, reviewed 2026-10-26; later registry changes and legal boundary accuracy unverified |
| OpenFreeMap basemap | Public Positron style loaded in the deployed browser; provider attribution preserved | Production browser verified; current public hosting terms apply |
| Mapterhorn DEM | Public TileJSON and terrain loaded in the deployed browser; provider/source attribution linked | Production 3D verified; provider source licences and service availability apply |
| Basins/rivers | Official ONWR 22-basin resource located; its specific license is not specified | Planned, disabled pending reuse terms and geometric acceptance |

References checked: [Open-Meteo API](https://open-meteo.com/en/docs), [terms](https://open-meteo.com/en/terms), [OpenGISData-Thailand pinned source](https://github.com/chingchai/OpenGISData-Thailand/tree/fafcea179cda88b689f5697c3866a449e79cd298), [OpenFreeMap quick start](https://openfreemap.org/quick_start/), [Mapterhorn attribution](https://mapterhorn.com/attribution/).

No source is declared production-ready based solely on appearing in the roadmap. Unconnected water/satellite/agency products are not shown as observations, warnings or safe conditions.

See [source acceptance investigation](source-acceptance.md) for actual probe results, official references and remaining dependencies.

The [RID acceptance record](rid-acceptance-2026-10-26.md) documents the narrower daily-storage scope, metadata capture and license interpretation. It does not grant acceptance to every RID product.
