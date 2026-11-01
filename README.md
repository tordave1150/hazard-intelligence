# Thailand Hazard Intelligence

Map usability update (1 November 2026): [separate water/rain cluster counts, shared overlay legend and wrapping mobile source notes](docs/map-legibility-release-2026-11-01.md).

Latest data release (30 October 2026): [national HII water and rain, 77-province comparison, 22-basin context and scheduler recovery](docs/province-rain-basin-release-2026-10-30.md). Seven independent products are connected; retrieval freshness and source observation time remain separate.

GISTDA update (29 October 2026): [retrospective three-day product, bounded pages and Actions cleanup](docs/gistda-three-day-release-2026-10-29.md). The active reader/publisher target `3days`; one-day products are historical. Complete production verification is recorded in the release evidence.

Previous release (28 October 2026): [Today modes, clock themes, hourly forecast and offline diagnostics](docs/current-execution-release-2026-10-28.md). The current GISTDA change is documented above.

Project scope: **Thailand nationwide**. See [current scope](docs/current-scope.md). Local examples and archived trials do not define defaults or preferred locations.


A single Thailand map for weather and water situation awareness, built with Next.js, TypeScript, MapLibre, deck.gl and independent Python ingestion. Active direction: [Roadmap V2](docs/THAILAND_HAZARD_INTELLIGENCE_ROADMAP_V2.md).

Project repository: [tordave1150/hazard-intelligence](https://github.com/tordave1150/hazard-intelligence). The legacy `weather_api` repository remains the migration baseline.

Daily and hourly weather each cover **77 provinces + 928 districts, 1,005 representative points** when a complete validated generation is published. RID supplies 35 daily large-dam storage reports. TMD CAP preserves original validity, cancellation references and polygons. GISTDA supplies the complete bounded retrospective **3days Thailand query**, with unknown acquisition time and distinct empty/unavailable states. HII / ThaiWater water-level and rain observations use independent national products and retain original wall times with unknown observation UTC/age. The 77-province comparison and separate 22-basin context are connected. National source queries do not certify complete station or satellite coverage. This build does not publish a flood-risk score, depth or ETA. See [current acceptance scope](docs/source-acceptance.md).

## Run locally

Requirements: Node.js 22+ and Python 3.11+ (tested with Node 26 and Python 3.13).

```powershell
npm ci
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r tests/requirements.txt
.\.venv\Scripts\python.exe -m pipelines.open_meteo.run --level all --export apps/web/data/local/weather.json
.\.venv\Scripts\python.exe -m pipelines.rid.run --export apps/web/data/local/dams.json
$env:HAZARD_LOCAL_SNAPSHOT='1'
npm run dev
```

Open http://127.0.0.1:3000. The local snapshot contains real API output, is ignored by Git and is disabled in production. The Python runner does not automatically load `.env` files. Review Open-Meteo access terms before fetching; the free API is non-commercial.

## Production architecture

- Vercel hosts `apps/web`, with read-only server APIs and server-only Atlas credentials.
- Independent GitHub Actions jobs fetch weather at 08:00 and RID at 08:15 Asia/Bangkok, without depending on website traffic.
- MongoDB holds independent A/B slots for weather (at most 2,010 documents) and dams (at most 70). Complete validated batches atomically promote their own control pointer. Failed ingestion retains the last good data. Historical collections are preserved.
- TMD CAP checks twice an hour and collects after one hour since success. Hourly weather checks each hour and collects after four hours or a new Bangkok day. Guarded skips do not change source timestamps. GitHub scheduling is best-effort.
- HII collects complete national automatic water-level and rain responses every two hours. Products publish independently with bounded A/B envelopes; station history uses a bounded server-side on-demand cache.
- Dam storage uses million m³ and percent of normal capacity, which can exceed 100%. Reports retain their calendar date and unknown observation instant when the forecast timeline changes.
- Administrative navigation retains canonical codes. The separate 22-basin dimension provides conservative HII station/RID point context, without inferred river-network connectivity or unsupported basin warnings.
- Rainfall amount and probability have distinct units, legends and semantics. Point forecasts are not area averages. All weather windows and retrieval times are disclosed.
- 2D uses deck.gl. MapLibre handles terrain and native 3D extrusion so polygons remain visible above terrain. Heights scale a selected weather metric, not water depth.

Production: [hazard-intelligence-lime.vercel.app](https://hazard-intelligence-lime.vercel.app/), using Atlas product snapshots. The [latest production receipt](docs/province-rain-basin-production-2026-10-30.json) records dated verification, not a promise of current freshness. Use `/health` for actual source status and the [operations runbook](docs/operations.md) for current commands.

คู่มือตั้งค่า Vercel ภาษาไทย: [วิธี Import repo และตั้งค่าโปรเจกต์](docs/VERCEL_SETUP_TH.md).

## Verify

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp artifacts/pytest-check
npm run typecheck
npm run test:web
npm run build
```

For running-app HTTP checks, set `HAZARD_TEST_URL=http://127.0.0.1:3000`. Test temp directories must be in a writable location; create the `artifacts` parent first if needed.

## Project map

| Path | Purpose |
|---|---|
| `apps/web` | Unified Next.js map, read APIs, source/methodology pages |
| `pipelines/open_meteo` | Real fetch, normalization and scheduled national runner |
| `pipelines/rid` | Independent documented daily-storage fetch and 35-dam publication |
| `pipelines/tmd` | Public CAP/RSS retrieval, references, polygons and bounded warning snapshots |
| `pipelines/thaiwater` | Independent national automatic water-level and rain observations |
| `pipelines/shared` | JSON Schema validation, time, coverage and A/B publication |
| `packages/contracts` | Shared language-neutral contracts |
| `data/boundaries/raw` | Preserved pinned boundary inputs |
| `apps/web/public/data` | Optimized region/province polygons and district files loaded by province |
| `tests` | Ingestion, geometry, atomicity, failure, legacy and optional HTTP checks |
| `docs` | Roadmap, audit, registry, map design, runbook and execution status |
| `app`, `etl` | Legacy Streamlit reference; not the production target |

Read the [data contract](docs/data_contract.md), [source registry](docs/source_registry.md), [map design](docs/map_design.md) and [operations](docs/operations.md). The original README is preserved as [legacy reference](docs/legacy_README.md).

## Attribution

Weather data: [Open-Meteo](https://open-meteo.com/), CC BY 4.0, subject to separate API access terms. Administrative boundaries: [OpenGISData-Thailand](https://github.com/chingchai/OpenGISData-Thailand/tree/fafcea179cda88b689f5697c3866a449e79cd298), CC BY 4.0 as published, simplified for display; upstream DOPA attribution retained. [Independent directory comparison](docs/dopa-geography-review-2026-10-26.md) corrected one district code and six Thai names using the official downloadable DOPA table dated 2023-09-01; later registry changes and legal geometry remain unverified. Embedded upstream postcode fields in raw inputs carry the [additional MIT notice](docs/THIRD_PARTY_BOUNDARY_NOTICES.txt). Basemap: OpenFreeMap / OpenMapTiles / OpenStreetMap. Terrain: Mapterhorn and its attributed source datasets.

HII / ThaiWater and original measuring agencies supply the connected national station products; public monthly archives are not substituted for current readings. Public access does not establish an unrestricted live-data licence or service guarantee. See [water-level acceptance](docs/hii-national-release-2026-10-30.md) and [rain/basin acceptance](docs/province-rain-basin-release-2026-10-30.md). GISTDA supplies the retrospective **3days** product with qualified reuse and unknown acquisition time. DDPM GIS supplies the attributed 22-basin context; no unrestricted basin-data licence is asserted.

Reservoir data: **ข้อมูลน้ำในอ่างเก็บน้ำ กรมชลประทาน (Royal Irrigation Department)**, [official catalog resource](https://data.go.th/th/dataset/reservoir2), [DGA Open Government License terms](https://data.go.th/th/pages/dga-open-government-license). The accepted daily-storage scope and exclusions are documented separately; no agency endorsement is claimed.

TMD CAP data: **กรมอุตุนิยมวิทยา / Thai Meteorological Department**, [public RSS channel](https://www.tmd.go.th/service/rss), feed-declared public domain and [attributed non-commercial republication terms](https://www.tmd.go.th/content/copyright). See the [CAP acceptance record](docs/tmd-cap-acceptance-2026-10-26.md).
