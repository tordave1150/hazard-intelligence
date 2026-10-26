# Thailand Hazard Intelligence

A single Thailand map for weather and water situation awareness, built with Next.js, TypeScript, MapLibre, deck.gl and independent Python ingestion. Active direction: [Roadmap V2](docs/THAILAND_HAZARD_INTELLIGENCE_ROADMAP_V2.md).

Project repository: [tordave1150/hazard-intelligence](https://github.com/tordave1150/hazard-intelligence). The legacy `weather_api` repository remains the migration baseline.

The live weather path covers **77 provinces + 928 districts, four forecast periods, 1,005 validated point forecasts**. The RID daily-storage adapter accepts 35 official large-dam reports with verified published point coordinates; see [product acceptance](docs/rid-acceptance-2026-10-26.md). River gauges, agency warnings, satellite products and basins remain planned until their own access, permission and data acceptance pass. This build does not publish a flood-risk score, depth or ETA.

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
- Dam storage uses million m³ and percent of normal capacity, which can exceed 100%. Reports retain their calendar date and unknown observation instant when the forecast timeline changes.
- Administrative navigation uses canonical source codes and a separate, currently disabled, basin dimension.
- Rainfall amount and probability have distinct units, legends and semantics. Point forecasts are not area averages. All weather windows and retrieval times are disclosed.
- 2D uses deck.gl. MapLibre handles terrain and native 3D extrusion so polygons remain visible above terrain. Heights scale a selected weather metric, not water depth.

Production: [hazard-intelligence-lime.vercel.app](https://hazard-intelligence-lime.vercel.app/), using Atlas weather snapshots. The Vercel connector still cannot see the deployed project; the GitHub connector cannot start Actions runs. These access limitations and the RID first-publication status are recorded in the [execution record](docs/execution-status.md) and [operations runbook](docs/operations.md).

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
| `pipelines/shared` | JSON Schema validation, time, coverage and A/B publication |
| `packages/contracts` | Shared language-neutral contracts |
| `data/boundaries/raw` | Preserved pinned boundary inputs |
| `apps/web/public/data` | Optimized region/province polygons and district files loaded by province |
| `tests` | Ingestion, geometry, atomicity, failure, legacy and optional HTTP checks |
| `docs` | Roadmap, audit, registry, map design, runbook and execution status |
| `app`, `etl` | Legacy Streamlit reference; not the production target |

Read the [data contract](docs/data_contract.md), [source registry](docs/source_registry.md), [map design](docs/map_design.md) and [operations](docs/operations.md). The original README is preserved as [legacy reference](docs/legacy_README.md).

## Attribution

Weather data: [Open-Meteo](https://open-meteo.com/), CC BY 4.0, subject to separate API access terms. Administrative boundaries: [OpenGISData-Thailand](https://github.com/chingchai/OpenGISData-Thailand/tree/fafcea179cda88b689f5697c3866a449e79cd298), CC BY 4.0 as published, simplified for display; upstream DOPA attribution retained. Embedded upstream postcode fields in raw inputs carry the [additional MIT notice](docs/THIRD_PARTY_BOUNDARY_NOTICES.txt). Basemap: OpenFreeMap / OpenMapTiles / OpenStreetMap. Terrain: Mapterhorn and its attributed source datasets.

Reservoir data: **ข้อมูลน้ำในอ่างเก็บน้ำ กรมชลประทาน (Royal Irrigation Department)**, [official catalog resource](https://data.go.th/th/dataset/reservoir2), [DGA Open Government License terms](https://data.go.th/th/pages/dga-open-government-license). The accepted daily-storage scope and exclusions are documented separately; no agency endorsement is claimed.
