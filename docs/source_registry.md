# Source registry

Machine-readable registry: `apps/web/data/source-registry.json`. It records endpoint/product reference, source category, authentication, licence, commercial and redistribution permission, quota, cadence/latency, coverage/resolution, units/CRS, fallback and terms-review date. `/sources` presents it; the map separately presents actual data age.

| Source | Evidence at 2026-10-25 | Release state |
|---|---|---|
| Open-Meteo daily forecast | Production run 40257438014 published and served 1,005/1,005 validated points, four daily periods, FRESH/SUCCESS on 2026-10-26; user confirmed non-commercial use | Connected on production; source attribution retained |
| RID reservoirs | Documented public endpoint probed: HTTP 200, 35/35 records and unique IDs; coordinates, flow units/window and reuse terms unresolved | Planned, disabled |
| TMD warnings/radar | Official portal and registration links verified; authenticated products and terms pending | Planned, disabled |
| HII / ThaiWater gauges | Official exchange standard reviewed; agency endpoint/access and live sample pending | Planned, disabled |
| GISTDA flood products | Official flood catalog reviewed; key required and dataset license unspecified; acquisition sample pending | Planned, disabled |
| Administrative boundaries | Pinned OpenGISData-Thailand commit, 77 provinces/928 districts, unique code and geometry QA; CC BY 4.0 as published by its author | Display geometry tested; independent current DOPA registry audit pending |
| OpenFreeMap basemap | Public Positron style loaded in the deployed browser; provider attribution preserved | Production browser verified; current public hosting terms apply |
| Mapterhorn DEM | Public TileJSON and terrain loaded in the deployed browser; provider/source attribution linked | Production 3D verified; provider source licences and service availability apply |
| Basins/rivers | No vetted geometry loaded | Planned, disabled |

References checked: [Open-Meteo API](https://open-meteo.com/en/docs), [terms](https://open-meteo.com/en/terms), [OpenGISData-Thailand pinned source](https://github.com/chingchai/OpenGISData-Thailand/tree/fafcea179cda88b689f5697c3866a449e79cd298), [OpenFreeMap quick start](https://openfreemap.org/quick_start/), [Mapterhorn attribution](https://mapterhorn.com/attribution/).

No source is declared production-ready based solely on appearing in the roadmap. Unconnected water/satellite/agency products are not shown as observations, warnings or safe conditions.

See [source acceptance investigation](source-acceptance.md) for actual probe results, official references and remaining dependencies.
