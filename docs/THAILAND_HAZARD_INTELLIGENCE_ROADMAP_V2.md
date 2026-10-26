# Thailand Hazard Intelligence — Unified National-to-Local Roadmap

> **Version:** 2.0  
> **Updated:** 2026-10-25 (Asia/Bangkok)  
> **Status:** Approved product direction / implementation roadmap; not a claim that proposed integrations are already operational  
> **Supersedes:** `WEATHER_API_REPO_UPDATE_ROADMAP_LATEST.md` as the **active execution roadmap**  
> **Companion:** `THAILAND_HAZARD_INTELLIGENCE_MASTER_PLAN.md` remains the **long-term research and digital-twin vision**  
> **Repository baseline:** `tordave1150/weather_api` (legacy Streamlit / Python ETL / MongoDB implementation)

---

## 0. Executive Decision Record

This version consolidates the agreed decisions from the project discussion. It **does not** instruct developers to build every long-term feature described in the Master Plan.

| Topic | V2 decision | Implementation consequence |
|---|---|---|
| Product | **Thailand Hazard Intelligence — Unified Weather & Water Monitoring** | One integrated geospatial experience, not separate operational pages per data type |
| Main screen | **Unified National-to-Local Hazard Intelligence Map** | Start at Thailand; progressively drill down by Region → Province → District, or by River Basin |
| Layer strategy | **All layers accessible from the same screen** | Smart defaults, toggles, filtering and zoom-dependent visibility; do **not** render all layers simultaneously at full detail |
| Frontend | **Next.js + React + TypeScript** | Replace Streamlit as the target deployed website |
| Hosting | **Vercel** | Host Next.js and read-only server APIs; do not run country-wide scheduled ETL inside page requests |
| Mapping | **MapLibre GL JS + deck.gl** | 2D/3D switching, terrain, district extrusion, multiple overlaid weather/water layers |
| Database | **MongoDB Atlas — Latest Snapshot with overwrite** | Bounded document count; no unlimited daily forecast snapshots |
| Ingestion | **Python ETL + GitHub Actions** | Fetch independently of website uptime; source-specific schedules |
| Source scope | **Open-Meteo + TMD + RID + HII/ThaiWater + GISTDA** | Integrate incrementally after checking actual endpoints, permissions, data formats and quality |
| Sentinel-1 | **Optional research / custom SAR processing** | Not part of MVP's mandatory data pipeline |
| ML / flood prediction | **Deferred** | No ML training, model registry, inference server or historical ML feature store in the MVP |
| Historical event replay | **Future research** | Not a required MVP feature; normal API-based historical lookup can remain |
| Refresh cadence | **Daily by default; faster only where genuinely useful and supported** | Weather forecast daily; rain radar/river gauges source-specific and age-labeled |
| Flood mapping | **GISTDA is satellite-observed flood extent, not live flood state** | Show satellite acquisition time and product age separately from data retrieval time |
| Operational warning | **Do not claim official or predictive flood warning** | Display agency warning products separately and attribute them explicitly |
| Cost | **Free-first, not free-unconditionally** | Check non-commercial terms, quotas, hosting/storage and redistribution before using each source |

### Non-goals for the MVP

- Nationwide hydrodynamic flood-depth simulation or real-time flood propagation physics.
- ML flood probabilities, river-height prediction, water-arrival ETA, GNN, advanced scenario simulation.
- Full historical forecast snapshot retention or event-replay database.
- Full PostGIS river topology database as a mandatory prerequisite for launching the map.
- Labeling satellite flood polygons as the current live flood boundary.
- A single composite national flood-risk score without a scientifically defined, validated methodology.

**Guiding principle:** Maintain an informative, attractive **2D/3D monitoring application**, while keeping costs, storage and operational complexity low.

---

# 1. Product Identity and Goals

## 1.1 Problem statement

ผู้ใช้ควรตอบคำถามจากหน้าจอเดียวได้ว่า:

1. วันนี้ **ประเทศไทยมีประเด็นอะไรที่ต้องติดตาม** บ้าง (ฝนมาก, ระดับน้ำสูง, สถานะเขื่อน, ประกาศหน่วยงาน, พื้นที่น้ำท่วมที่ดาวเทียมเคยตรวจพบ)
2. **จุดไหน/ภาคไหน/จังหวัดไหน** มีข้อมูลน่าสนใจหรือผิดเกณฑ์ของแหล่งข้อมูลนั้น
3. กดจากแผนที่ประเทศไทยลงไปที่ **Region → Province → District** ได้โดยไม่ย้ายหน้า
4. เปิดดูอีกมุมมองเป็น **River Basin / Catchment** ได้ เพราะระบบน้ำไม่ได้ตามขอบเขตปกครอง
5. เมื่อเลือกพื้นที่หนึ่ง ระบบรวมข้อมูลที่เกี่ยวข้องจากทุกแหล่งใน **Area Intelligence Panel**
6. แยกได้ว่าอะไรเป็น **Observed**, **Forecast**, **Agency Warning**, **Satellite Observation**, หรือ **Scenario/Model** (แบบหลังไม่อยู่ใน MVP)
7. เห็น **เวลาที่ข้อมูลถูกสังเกตจริง** และเวลา **ระบบได้รับข้อมูล** เพื่อประเมินความสด

## 1.2 Product promise

> **One map. Multiple verified data sources. National overview to local understanding.**

เป้าหมายของ MVP คือ **Weather & Water Situation Awareness** ไม่ใช่ระบบคำนวณล่วงหน้าว่าพื้นที่ใดจะน้ำท่วมจาก ML.

## 1.3 Main user journey

```text
Open Web App
     ↓
Thailand National Overview
     ↓
See notable rainfall / water / agency warnings / satellite flood observations
     ↓
Select Region OR River Basin
     ↓
Zoom to Province / District
     ↓
Inspect combined area intelligence
     ↓
Toggle weather / river / dam / flood / terrain and 2D/3D
     ↓
Read individual source timestamps, measurements and provenance
     ↓
Back to National (without leaving the main page)
```

---

# 2. Target Architecture — Vercel + Latest Snapshot

## 2.1 End-to-end system

```text
                  EXTERNAL SOURCES
      ┌───────────┬───────────┬──────────┐
      │Open-Meteo │    TMD    │   RID    │
      └───────────┴───────────┴──────────┘
      ┌────────────────┬──────────────────┐
      │ HII / ThaiWater│ GISTDA Products │
      └────────────────┴──────────────────┘
                        │
                        ▼
             GitHub Actions + Python ETL
         Fetch → Validate → Normalize → QC
                        │
                        ▼
             MongoDB Atlas (bounded)
             ├─ weather_latest
             ├─ tmd_latest
             ├─ dam_latest
             ├─ gauge_latest
             ├─ flood_metadata_latest
             ├─ source_status
             └─ active_snapshot / run status
                        │
                        ▼
          Next.js server-side read APIs
             Normalization + caching
                        │
                        ▼
                Vercel / Next.js
          Unified Situation Map (one page)
              ├─ MapLibre GL JS
              ├─ deck.gl
              ├─ 2D / 3D Terrain
              ├─ National / Region / Province / District / Basin
              ├─ Layer controls + Timeline
              ├─ Area Intelligence Panel
              └─ Data Freshness / Sources

      STATIC / EXTERNAL GEOSPATIAL ASSETS
      Boundaries / Terrain / PMTiles / authorized
      WMS / WMTS / raster tile services
                        │
              Browser map renderer
```

**Important:** Flood raster tiles, satellite imagery and large boundary polygons should not be inserted into MongoDB document fields by default. Use approved remote tile services or object/static hosting; keep reference URLs, version, extent, acquisition time and metadata in MongoDB.

## 2.2 Runtime responsibilities

| Component | Responsibility | Must not do |
|---|---|---|
| GitHub Actions | Scheduled or manual ingestion; source-level QC and publish | Depend on Vercel website being online |
| Python ETL | API adapters, transform, schema validation, bounded writes | Append an unlimited history by default |
| MongoDB Atlas | Latest valid normalized snapshots, selected short rolling gauges, source health | Store raw satellite scenes or all daily history indefinitely |
| Next.js API / Server Components | Read MongoDB, validate input, sanitize responses, cache | Ship MongoDB URI or source API keys to browsers |
| Vercel | Web app hosting and lightweight read traffic | Run long country-wide ingestion when a visitor opens the page |
| MapLibre + deck.gl | Base map, zoom, polygons, 3D, layer composition | Infer hazard causality or flood depth from styling alone |
| External tile services | Serve map tiles / satellite layers when licensed | Be treated as guaranteed free without verifying terms |

## 2.3 Why MongoDB remains

The accepted choice is **Choice B: Latest Snapshot Overwrite** rather than database-free operation. Reasons:

- Vercel/Next.js restart must not trigger a new nationwide weather fetch.
- Website reads the **last successfully published data** while source APIs temporarily fail.
- Only one logical active snapshot per location/source/product is needed; storage does not grow linearly with calendar dates.
- Source-specific freshness can be displayed even if individual providers update at different intervals.

A latest-snapshot store is **not a database backup** and does not protect against total loss of MongoDB. The system is resilient to website restarts and some upstream failures, not to permanent database loss.

---

# 3. Core Experience — Unified National-to-Local Map

## 3.1 Single-page principle

**The main application is one integrated screen.** Weather, radar, rain gauges, river gauges, dams, warnings, flood extents and terrain are selectable layers within the same geographic context; they are not independent mandatory pages.

Dedicated pages may still exist for **About / Data Methodology / Source Status / Legal**, but the operational interaction should happen in a **single `/` or `/map` experience**.

## 3.2 Desktop wireframe

```text
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ THAILAND HAZARD INTELLIGENCE                 Search Area       Latest Source Status  2D/3D│
├─────────────────────────────────────────────────────────────────────────────────────────┤
│  Weather summary     Rain gauges / River status     Dam status     Satellite observations │
│  (source-specific, not a composite unverified national flood-risk score)                 │
├───────────────────┬───────────────────────────────────────────────┬─────────────────────┤
│ LAYER CONTROLS    │                UNIFIED MAP                    │ AREA INTELLIGENCE   │
│                   │                                               │ (selected geography)│
│  ☑ Rainfall       │   Thailand → Region → Province → District      │                     │
│  ☑ Agency Alerts  │   OR River Basin / Sub-basin                   │ Rain / Forecast     │
│  ☑ River Gauges   │                                               │ River / Gauge       │
│  ☑ Dam Status     │   2D / 3D Terrain / Extrusion / Satellites    │ Dam / Release       │
│  ☐ Flood Extent   │                                               │ Flood Observations  │
│  ☐ 3D Terrain     │   Map legend + selected source/time badges    │ Sources & Freshness │
│                   │                                               │ Mini charts when    │
│ GEOGRAPHY         │                                               │ source data supports│
│ National          │                                               │ them                │
│ Region            │                                               │                     │
│ Province          │                                               │                     │
│ District          │                                               │                     │
│ Basin             │                                               │                     │
├───────────────────┴───────────────────────────────────────────────┴─────────────────────┤
│ TIMELINE: OBSERVED ◄────────── NOW ──────────► FORECAST                            Reset │
│ Individual dataset timestamp and validity windows (NOT fake synchronized live frames)  │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### Layout rules

- **Map-first:** Map occupies the majority of available desktop space.
- **Left panel:** Collapsible layer and geography controls.
- **Right panel:** Contextual information, empty until an area/station is selected; collapsible.
- **Top summary:** A compact national overview of actual measurements, mapped thresholds and official products; source-specific statuses only.
- **Bottom timeline:** Supports meaningful time navigation only for available forecast or timestamped observations. Do not invent continuous replay between sparse satellite acquisitions.
- **Source badges/legend:** Indicate source, unit, state (Observed/Forecast/Satellite/Warning), and age.
- **Responsive:** On mobile convert side panels into bottom sheets/drawers with the map still central.

## 3.3 Drill-down behavior

| Geographic context | Primary presentation | Detail rule |
|---|---|---|
| **National** | Thailand-wide weather overview, agency warning areas, clustered gauge/dam markers, newest satellite observations (conditionally visible) | No thousands of station labels; generalized polygons and clustering |
| **Region** | Provinces within selected region; concentration of notable source-specific observations | Summary of provinces; region is an administrative aggregation, not a watershed |
| **Province** | District boundaries, rainfall by supported resolution, river gauges, dams, eligible flood polygons, 3D terrain | Cross-filter Area Intelligence panel |
| **District / Local** | Relevant local stations and measurements; actual available flood observations; local terrain/river overlays | Display nearest station distance and coverage, not fabricated district-average readings |
| **River Basin / Sub-basin** | Upstream/downstream watershed geography with gauges, dams and catchment rainfall when meaningful | Basin hierarchy separate from Region → Province → District |

Navigation:

```text
Thailand / Northern Region / Chiang Rai / Mae Sai

OR

Thailand / Basin View / [Verified Basin] / [Verified Sub-basin]
```

Clicking an area should **zoom**, **filter**, **update panel**, and **preserve chosen map layers**. A prominent **Back to Thailand** action and breadcrumb support the return trip. Use a clear selection state and map popups without duplicating the whole right-side panel.

## 3.4 How layers coexist without clutter

**Layer availability ≠ layer always visible.** All eligible datasets can be accessed from the main page, while defaults and zoom rules keep the map legible.

Suggested national default:

1. Weather/rainfall thematic layer (selected measured or forecast period, clearly labeled).
2. Agency official warning polygons or markers, if data actually available.
3. Clustered river gauges and dams with category icons.
4. Satellite flood observation overlay **optional** at national zoom, only with its acquisition time/coverage shown.
5. Terrain off or low-intensity hillshade at national scale; user can enable 3D.

As the user zooms in, show more individual markers, river geometry, precise polygon boundaries and 3D. Avoid full-detail station labels, intense animations, heavy 3D extrusions and dense rain layers all at the same time.

## 3.5 Area Intelligence Panel

For any selected Region/Province/District/Basin:

```text
Area / Region / Basin identity
├─ Weather current / observed variables
├─ Forecast rainfall / probability / valid period
├─ Nearby rain gauges (if available)
├─ Relevant river gauges, levels, trend (if time series available)
├─ Relevant dams, storage, inflow, outflow (if available)
├─ Satellite-observed flood extent (date, coverage, source)
├─ Official agency warning products (separate classification)
├─ Quality / freshness / missing-source disclosures
└─ Source references and measurement timestamps
```

A source with no coverage or outdated records is displayed as **No data / Stale / Unavailable**, not silently interpreted as **Normal**.

---

# 4. 2D/3D Map Design — Retained Core Feature

## 4.1 3D is in-scope despite no ML

**3D stays a core visual feature.** Cutting ML and historical accumulation does **not** require cutting MapLibre/deck.gl terrain or extrusion.

| Feature | MVP status | Meaning |
|---|---|---|
| Interactive national 2D map | Required | Clear baseline situation map |
| 2D/3D toggle | Required | User-controlled perspective and terrain |
| 3D Terrain / hillshade | Required where terrain tiles and suitable licensing are available | Physical elevation context |
| 3D district extrusion | Required in appropriate local/regional views | Height represents a **specific selected metric**, not floodwater depth |
| River/dam/gauge overlays | Required when source coverage available | Geographic visualization of actual readings |
| Satellite flood extent | Required when licensed/available | Observed at satellite acquisition time |
| Animated flood movement / fluid mechanics | Deferred | Requires hydraulic/hydrology model and validation |
| Predicted flood depth or ETA | Deferred | Cannot be inferred from visualization alone |
| Historic 3D event replay | Deferred | Needs independent dated observations, histories and validation |

## 4.2 Map modes

```text
VIEW MODE
- 2D Flat
- 3D Terrain
- 3D Extrusion (where relevant metric is selected)

METRIC MODE
- Rainfall amount (mm / explicitly stated time window)
- Rain probability (%) — separate, never titled rainfall intensity
- River gauge level (m, station reference datum)
- Dam storage (%) / discharge (m³/s)
- Satellite-observed flood extent (observed polygon, NOT height)
```

Geometry extrusion example:

```text
District column height = display-scale transformation of forecast rainfall (mm/24h)
Color = rainfall amount class for that same valid time window
Tooltip = exact metric, unit, source, valid time, geometry aggregation method
```

Do not apply district-height extrusions from point-forecast values as though they were measured area-wide without labeling the aggregation/representativeness limitation.

## 4.3 Information density by zoom

```text
National      Low-detail weather + agency advisories + clusters
Region        Province/district overview with selective overlays
Province      Detailed rainfall / gauges / major rivers / terrain
District      3D terrain + local stations / river / satellite extent
Local         Individual geographic features only where coverage exists
```

Use zoom-dependent LOD and vector tiles / PMTiles where possible. Preserve original geometries separately from display-simplified versions.

## 4.4 Visual semantics

- **Rainfall** uses a clear sequential quantitative palette with legend and `mm / time window`.
- **Probability** uses a separate `%` legend and labels like **Chance of Rain**; never call a high rain probability **Heavy Rain** by itself.
- **Official warnings** display agency wording/categories and source clearly; do not transform into unofficial hazard authority.
- **Water level** uses station-specific actual units and published thresholds, if available.
- **Satellite flood polygons** use a distinct overlay with acquisition date and an explanation that the scene may not represent current conditions.
- **Missing and stale** are neutral/unavailable, **not green/low risk**.
- Provide color-blind-friendly differentiation, selectable layer opacity, and a legible legend.

---

# 5. Data Source Inventory and Integration Strategy

## 5.1 Source roles

| Source | Target data | Role in MVP | Integration status/constraint |
|---|---|---|---|
| **Open-Meteo** | General weather forecast, rainfall history on demand | Initial weather backbone | Existing repo fetch is documented; verify current quotas/license before deployment |
| **TMD** | Official Thai weather forecasts, radar and warnings | Agency weather evidence, radar/alerts | Endpoint, format, terms and actual refresh must be validated per product |
| **RID** | Reservoir storage, inflow/outflow, dam operations | Dam monitoring | Validate specific public API schema, units, station IDs and terms |
| **HII / ThaiWater** | Rain gauges, river/water-level stations | Near-real-time situation monitoring | Authentication, accessible datasets, station coverage and latency must be confirmed |
| **GISTDA** | Processed flood extent and satellite flood products | Satellite-observed flood evidence | Product scope/availability and geospatial API permissions vary; not real-time |
| **Sentinel-1 (SAR)** | Raw radar scenes for custom inundation extraction | Optional later research | Requires image processing and quality control; not faster simply because raw imagery is used |
| **DEM / administrative boundaries** | Terrain, regions, provinces, districts, basins | Static base layers and optional 3D | Validate provenance, CRS, geographic IDs and re-use terms |
| **WeatherNext** | Advanced model forecast datasets | Deferred | Not required for MVP; research/operational permissions distinct |

**Integration status labels:** `Existing legacy adapter`, `Candidate — verify`, `Connected / tested`, `Production ready`, `Unavailable`. Never mark a service as connected solely because it appears in this roadmap.

## 5.2 Acquisition strategy

- **Source-specific adapters** live in `pipelines/<source>/`.
- Each adapter implements discovery/authentication, fetch, normalization, validation, health metrics and publication.
- Link every source record to official dataset/product name, geographic coverage and cadence.
- API availability does not guarantee redistribution rights or unrestricted commercial usage.
- Prefer **data already processed by an authoritative provider** for the MVP; custom Sentinel-1 segmentation can follow as independent research.

## 5.3 Source freshness is not one global timestamp

Examples:

```text
Open-Meteo forecast        → forecast_reference_time / valid_time / fetched_at
TMD radar                  → radar_scan_time / fetched_at
HII gauge                  → observed_at / fetched_at
RID dam                    → report_date / observed_at / fetched_at
GISTDA satellite product   → satellite_acquired_at / published_at / fetched_at
```

**A freshly fetched 3-day-old satellite polygon remains a 3-day-old observation.** It is never re-labeled as live just because the API returned it today.

---

# 6. Refresh Policy — Source-Specific, Bounded

## 6.1 Proposed refresh schedule (not provider guarantees)

| Dataset | Initial policy | Why |
|---|---|---|
| Weather forecast / nationwide | **Once daily**; optional second fetch only if justified | Controls calls; broad outlook |
| TMD official forecast / warnings | Daily baseline; **poll more often for warnings if endpoint and quota permit** | Official updates may not follow daily schedule |
| Rain radar | **Source-appropriate near-real-time** when authorized; do not force daily only | Rain systems evolve faster than daily reports |
| HII rain/river gauges | **1–3 hours where access and update cadence support it**; adapt per station | Trends need current measurements |
| RID reservoir/dam | Daily or match the reporting cadence | Dam reports may have discrete updates |
| GISTDA flood extent | Daily metadata check / after new products | Observation cadence depends on satellites and processing |
| Historical weather | On-demand; optional ephemeral cache | No permanent history accumulation required |
| Administrative / terrain | Only when static datasets change | No daily refetch |

If the project decides to run **all upstream ETL only once daily**, the user interface must explicitly present gauge/radar data as the **latest available daily snapshot**, not as near-real-time monitoring. Operational flood/flash-flood warning claims are out of scope under that constraint.

## 6.2 Schedules and freshness must be separate

- `last_fetch_attempt`: our latest attempt.
- `last_successful_fetch`: our latest successful ingest.
- `observed_at` / `satellite_acquired_at`: actual measurement time.
- `valid_time`: future timestamp for forecast values.
- `source_updated_at` / `published_at`: provider release time, where known.
- `staleness`: computed using **observation age**, **known source cadence**, and an explicit rule per dataset.

Status enum:

```text
FRESH
DELAYED
STALE
UNAVAILABLE
UNKNOWN
```

Do not infer the freshness status from `fetched_at` alone. A product may be **Fetched recently / Observed 72h ago**.

---

# 7. MongoDB Latest Snapshot Design

## 7.1 Bounded collections

```text
weather_latest             # source + location + product/lead window
agency_weather_latest      # TMD advisories / forecast products
river_gauge_latest         # each station's last valid reading
rain_gauge_latest          # each station's last valid reading
dam_latest                 # each dam's last valid publication
flood_metadata_latest      # satellite product pointer / extent metadata
source_status              # source/product health and freshness
snapshot_control           # active snapshot generation per product
```

**Optional** `gauge_recent` collection / embedded bounded array: a deliberately small recent trend window (for example <=24h) with cap/TTL. Disable by default if storage or provider terms prevent it.

## 7.2 Unique identity and overwrite

Long-term key design:

```text
weather_latest:  (source_id, product_id, location_id, lead_or_valid_period)
river_gauge_latest: (source_id, gauge_id, metric_type)
dam_latest: (source_id, dam_id, product_id)
flood_metadata_latest: (source_id, product_id, coverage_id)
```

Use **stable source-native IDs mapped to canonical IDs**, not location names alone. Match unique indexes to the actual key. **Do not use daily `date` as a growing primary partition for latest-snapshot collections.**

Example normalized weather document (illustrative values; not actual weather):

```json
{
  "source_id": "open_meteo",
  "product_id": "daily_forecast",
  "location_id": "TH-DISTRICT-EXAMPLE",
  "data_state": "forecast",
  "forecast_reference_time": "2026-10-25T01:00:00Z",
  "ingested_at": "2026-10-25T01:15:00Z",
  "valid_periods": [
    {"date": "2026-10-25", "rainfall_mm": 12.5, "rain_probability_pct": 70},
    {"date": "2026-10-26", "rainfall_mm": 8.0, "rain_probability_pct": 45}
  ],
  "schema_version": "2.0"
}
```

The sample location ID is a placeholder; actual administrative codes must come from a validated authoritative registry.

## 7.3 Last-good-data and partial-run protection

**Minimum V1:**

1. Fetch and validate each source product.
2. Reject invalid or empty documents.
3. Only replace a record after its new version passes validation.
4. Update `source_status` and `last_successful_fetch` correctly.
5. If a fetch fails, retain the last good record and display `STALE` if its age exceeds the threshold.

**Stronger recommended method for nationwide publication:** **A/B bounded snapshot slots** per product/source:

```text
Active slot A (last good complete batch)
       │
Fetch and write candidate slot B
       ↓
Validate coverage / IDs / completeness / date range
       ↓
Atomically change active-slot pointer B
       ↓
Reuse slot A on next publication cycle
```

This uses at most **two retained generations** of a relevant source product rather than unbounded history. A/B is especially useful when 990 nationwide locations update at different times and users must not see half of yesterday plus half of today as a supposedly complete new batch.

Different sources are not guaranteed to have the same observation time: **cross-source simultaneity must never be implied**. No new source batch should publish if coverage/quality requirements are not met.

## 7.4 Database capacity and retention

- Aim for a **bounded count by active locations/stations/products**, not by elapsed days.
- Keep images/large raster and vector tiles outside MongoDB.
- Review database data and index size under the actual free-tier constraints rather than relying on sample size estimates.
- Set maximum list lengths, payload size limits and explicit TTL only for genuinely ephemeral caches.
- Old **legacy** history collections must not be deleted automatically during migration; review migration and recovery needs first.
- Daily overwrite eliminates most data growth but **does not eliminate quota, concurrency, bandwidth or availability constraints**.

---

# 8. Canonical Data Contracts and Semantics

## 8.1 Required data-state separation

| `data_state` | Meaning | Example |
|---|---|---|
| `observed` | Actual measurement at instrument/scan time | HII gauge reading, radar scan |
| `forecast` | Valid for future time | Open-Meteo rainfall prediction |
| `agency_warning` | Official agency information | TMD warning product |
| `satellite_observation` | Derived from satellite acquisition at an earlier time | GISTDA flood extent |
| `modeled` | Model-derived experimental value | Deferred; no operational ML MVP |
| `scenario` | User-generated what-if | Deferred |

## 8.2 Minimal schemas

```text
Location
  location_id, location_type, parent_id, name_th, name_en,
  source_aliases, geometry_ref, valid_from, valid_to

WeatherObservation
  source_id, location_id/point, metric_type, value, unit,
  observed_at, ingested_at, quality_status, schema_version

Forecast
  source_id, location_id/point, metric_type, value, unit,
  forecast_reference_time, valid_start, valid_end,
  forecast_horizon, ingested_at, schema_version

WaterGauge
  source_id, gauge_id, geometry, metric_type, value, unit,
  observed_at, station_datum, threshold_definition, ingested_at

DamObservation
  source_id, dam_id, storage_pct, storage_volume,
  inflow, outflow, unit_metadata, observed_at, ingested_at

SatelliteFloodProduct
  source_id, product_id, satellite/acquisition_time, published_at,
  downloaded_at, coverage_geometry, tile_or_layer_ref,
  processing_method, product_quality, license_metadata

AgencyWarning
  source_id, warning_id, area, issued_at, effective_start,
  expires_at, agency_severity, content_ref, last_updated_at

SourceStatus
  source_id, dataset, last_attempt, last_success,
  observation_age, completeness, quality, access_status
```

## 8.3 Weather semantics bug that still needs correction

Legacy repo reports rainfall probability (%) with intensity labels such as `Heavy Rain` while historical rain uses millimeters. **These are fundamentally different metrics**. Correct them before display layers are launched.

```text
Chance of Rain:  80%     # likelihood, not intensity
Rainfall Total:  12 mm   # accumulation period must be explicit
```

Likewise, **rainfall observation**, **flood observation**, **flood probability**, and **official flood warning** are different concepts.

## 8.4 Time and provenance conventions

- Store instants in UTC with timezone-aware formats; convert to Asia/Bangkok for display.
- Daily accumulation periods must explicitly state their timezone and start/end.
- Keep units and station datums attached to measurements.
- Distinguish provider/model reference time from our ingest time.
- Keep source product IDs and official documentation URLs.
- Missing readings remain `null`/unknown, never silently coerced to 0.
- Record any district-level forecast aggregation from point/grid resolution and warn when spatial representativeness is limited.

---

# 9. Administrative Geography and River Basins

## 9.1 Canonical administrative IDs

Use vetted Thai Ministry of Interior administrative codes for province, district and subdistrict mapping where applicable. Preserve names and aliases but do not treat strings as primary join keys. ISO 3166-2 may be stored as an alternative province-level code where appropriate, not as a district canonical ID.

Geographic examples:

```text
province_id
  └─ district_id
       └─ subdistrict_id
```

`region_id` must come from a declared region classification (e.g., 4/6-region convention) and remain versioned; do not assume all agencies define regions alike.

## 9.2 Basin dimension is separate

```text
Administrative hierarchy: Thailand → Region → Province → District
Hydrological hierarchy:   Thailand → River Basin → Sub-basin → River segment
```

A district may intersect multiple basins. Relations should be computed using verified spatial geometry and intersection logic, not guessed by name.

**V2 MVP can show basin polygons and associated stations** if a trustworthy dataset is available; building a fully validated directed river-routing graph remains optional future hydrology work.

## 9.3 Geospatial asset strategy

```text
Raw Geometry (preserved)
      ↓
Geometry validation / CRS / canonical IDs
      ↓
Simplification + LOD
      ↓
Static GeoJSON for limited small layers
      OR
Vector Tiles / PMTiles for larger layers
      ↓
MapLibre / deck.gl
```

Do not overwrite raw geometry during simplification. Verify feature count, IDs, area differences, validity and visual appearance.

---

# 10. Layer Specifications and UI Data Semantics

| Layer | Map form | Aggregation/zoom strategy | Status source | Required tooltip |
|---|---|---|---|---|
| Forecast rain amount | Choropleth/grid | National generalized; local if actual resolution permits | Open-Meteo | mm per period, valid dates, model source |
| Rain probability | Alternative thematic view | **Do not merge** with rain amount class | Open-Meteo | %, forecast valid period |
| Radar / observed rain | Raster tiles or available station symbols | Source coverage and update age | TMD / HII where accessible | scan/observed time, intensity unit |
| River gauges | Cluster → individual station | Show station readings, not fabricated interpolated river level | HII where accessible | value, unit, datum, time, threshold source |
| Dams | Clusters → facility markers | Scale by zoom and selected basin | RID | storage %, inflow/outflow and times |
| Agency warnings | Official polygon/marker | Keep official scope and severity labels | TMD/other authorized | issuing agency, issue/effective/expiry |
| Satellite flood extent | Raster/polygon overlay | Only where acquired/available | GISTDA | acquisition date, product, coverage, confidence/QA if published |
| Basins/rivers | Static verified GIS vectors | Major basin national → details at zoom | validated GIS sources | geometry/source/version |
| 3D Terrain | DEM terrain raster | Adaptive zoom/LOD | permitted terrain provider | elevation source/version |
| 3D district extrusion | Polygon elevation by selected **data metric** | Province/district contexts | normalized weather/water metric | scale meaning, source and time |

### Layer compatibility rules

- Layers with conflicting color scales should not both dominate the map; opacity/reordering or a split thematic mode should be available.
- A heavy-rain **forecast** overlay and satellite **observed flood** polygon may coexist only with clear legends and times.
- Rivers and dams may cross provincial boundaries; selecting one district must not hide important upstream context if available.
- Default summary cards should count **source observations above published thresholds** rather than invent a unified hazard score.
- If a data source lacks published thresholds, show the value/rank/percentile descriptively and label the basis clearly.

---

# 11. Historical, Replay and Satellite Scope

## 11.1 Historical weather in the current app

- Historical weather may remain **on-demand via an approved archive API**.
- A short-lived application/server cache is allowed; no automatic permanent snapshots.
- The Historical ETL misrouting identified in prior repo review must be fixed or retired during migration.
- An archive of past **observations** is not the same as an archive of what **forecasts issued at the time** predicted.

## 11.2 Event Replay (deferred)

The Master Plan's Pua/Nan, Mae Sai, Hat Yai, Bangkok 2011 and other historical cases remain in the **research backlog**, not the committed MVP. If resumed, they require dated source data, rigorous separation of observations/inference and licensing review.

## 11.3 GISTDA vs Sentinel-1

```text
GISTDA processed flood product
        ↓
Latest available satellite-based flood footprint
        ↓
Licensed raster/vector/map service
        ↓
Show on unified map with acquisition time

Sentinel-1 raw SAR (optional future)
        ↓
Calibration / preprocessing
        ↓
Before-after water detection
        ↓
Terrain / permanent-water / urban false-positive controls
        ↓
Validation against known flood products
        ↓
Map layer with method + uncertainty
```

Neither satellite path guarantees real-time coverage. A regular **API poll** does not create a new satellite acquisition.

---

# 12. ETL Operations and Quality Gates

## 12.1 Recommended ETL package layout

```text
pipelines/
├─ shared/
│  ├─ schemas.py
│  ├─ quality.py
│  ├─ locations.py
│  ├─ time_units.py
│  └─ publication.py
├─ open_meteo/
├─ tmd/
├─ rid/
├─ thaiwater/
└─ gistda/
```

Keep provider-specific fetch semantics out of browser UI. Separate `client`, `transform`, `validate`, `publish` inside an adapter as complexity warrants; do not split into many files just for the sake of refactoring.

## 12.2 ETL quality requirements

1. **Idempotent:** Re-running an ingestion does not accumulate date-stamped duplicates.
2. **Validated:** Units, times, source IDs, geography and required fields pass validation.
3. **Completeness-aware:** Missing providers/locations are measured; do not mark whole country fully updated after partial failure.
4. **Retryable and rate-limit aware:** Exponential backoff as allowed by provider terms.
5. **Observable:** Store per-source run metrics, success/failure and counts.
6. **Last-good:** Preserve last published data on failed fetch.
7. **Bounded:** No uncontrolled raw response retention or growing full-history collections.
8. **Security:** Secrets in approved CI/Vercel secret storage; least-privilege access.

## 12.3 Log fields

```text
etl_run_id
source_id / product_id
started_at / completed_at
requested_locations
successful_locations
missing_locations
records_validated
records_published
last_successful_fetch
active_generation
status / error_summary
```

---

# 13. Free-First Operations and Source Registry

## 13.1 Free means different things

Always separately verify:

- Free API access vs free commercial use.
- Access rights vs reuse/redistribution rights.
- Research/free quotas vs operations at public production scale.
- Free dataset vs paid/limited storage, tiles, bandwidth or hosting.
- Open data vs API endpoint requiring registration/token.

No provider's current terms or uptime is guaranteed by this document. Validate directly with the provider when onboarding the dataset or changing deployment terms.

## 13.2 Required source registry

```text
source_id
organization
product_name
endpoint_or_tileset
authentication_method
license / attribution
commercial_permission
redistribution_permission
request_quota / rate_limit
observed_update_frequency
expected_publication_latency
spatial_coverage / spatial_resolution
temporal_resolution
units / coordinate_reference_system
provider_product_reference
fallback_behavior
last_terms_reviewed
integration_status
```

Use a source status panel so users can see per-dataset data age, coverage and errors. This registry can begin in version-controlled YAML/JSON rather than a new database.

---

# 14. Proposed Repository Evolution

## 14.1 Monorepo target (incremental)

```text
hazard-intelligence/
├─ apps/
│  └─ web/                   # Next.js / Vercel app
│     ├─ app/
│     │  ├─ page.tsx         # Unified Map main screen
│     │  ├─ api/             # Read-only query endpoints
│     │  ├─ methodology/
│     │  └─ sources/
│     ├─ components/
│     │  ├─ map/
│     │  ├─ layers/
│     │  ├─ geography/
│     │  ├─ area-panel/
│     │  └─ timeline/
│     └─ lib/
│        ├─ api/
│        ├─ schemas/
│        └─ map/
├─ pipelines/                # Python adapters run via GitHub Actions
│  ├─ shared/
│  ├─ open_meteo/
│  ├─ tmd/
│  ├─ rid/
│  ├─ thaiwater/
│  └─ gistda/
├─ packages/
│  └─ contracts/             # Shared JSON Schemas / type generation
├─ data/
│  ├─ boundaries/raw/
│  ├─ boundaries/web/
│  ├─ basins/
│  └─ tiles/
├─ docs/
│  ├─ source_registry.md
│  ├─ data_contract.md
│  ├─ map_design.md
│  └─ operations.md
└─ tests/
```

**Migration principle:** Keep the legacy Streamlit app as a known-good reference during development; production target is **Vercel**, not simultaneous Streamlit deployment. No forced rewrite of healthy Python fetch/transform logic when reuse is possible.

## 14.2 Read API sketch

```text
GET /api/overview
GET /api/areas?level=region|province|district|basin
GET /api/area/{location_id}/summary
GET /api/weather?area_id=&valid_date=&metric=
GET /api/gauges?area_id=&kind=river|rain
GET /api/dams?area_id=
GET /api/warnings?area_id=
GET /api/flood-products?area_id=
GET /api/sources/status
```

Server API must enforce bounded queries, caching and output schemas. Never expose database connection details. Basemap/vector/raster tile access should use documented and authorized paths distinct from JSON read APIs.

---

# 15. Delivery Roadmap — Updated V2

> **No ML or Event Replay dependency for V2 launch.** Source integration and 3D map can advance in parallel after minimal contracts are established.

## Phase 0 — Protect and audit legacy system

**Tasks**

- [ ] Preserve/tag known-good `weather_api` commit and capture current deployment behavior.
- [ ] Confirm current repo code and dependencies (README may be outdated).
- [ ] Reproduce historical refresh mismatch and precipitation-probability label mismatch before fixing.
- [ ] Record current MongoDB collection counts, indexes and storage size.
- [ ] Measure forecast ETL counts, failure rates and map asset sizes.
- [ ] Verify current license/usage restrictions of existing weather endpoints.

**Deliverable:** Reproducible baseline; no destructive DB cleanup.

## Phase 1 — Canonical semantics + bounded data model

**Tasks**

- [ ] Define weather vs water vs satellite vs warning source states and timestamps.
- [ ] Fix rain probability / rain volume naming and unit/window display.
- [ ] Establish administrative canonical IDs and source-to-ID mapping.
- [ ] Define minimal JSON schemas and validation tests.
- [ ] Design Mongo latest collections, unique indexes, last-good-data rules.
- [ ] Decide which products require A/B snapshot promotion and which can use per-record overwrite.

**Deliverable:** Shared contract and safe latest-snapshot publication design.

## Phase 2 — Scheduled ingestion + MongoDB migration

**Tasks**

- [ ] Convert existing Open-Meteo pipeline to bounded latest snapshots.
- [ ] Separate UI query from ETL job execution.
- [ ] Add source status, time metadata, quality and coverage checks.
- [ ] Implement last-successful snapshot fallback.
- [ ] Test ETL scheduled runs independently of frontend availability.
- [ ] Preserve old historical collections until migration review is complete.

**Deliverable:** Dependable weather ingestion that survives a Vercel server restart without nationwide re-fetch.

## Phase 3 — Next.js/Vercel Unified Map MVP

**Tasks**

- [ ] Scaffold Next.js/TypeScript/Vercel web application.
- [ ] Build **one-page map-first** layout and responsive panels.
- [ ] Build Thailand national overview and region/province/district selection.
- [ ] Add basemap, canonical polygons, breadcrumbs, map-based search.
- [ ] Add Area Intelligence Panel and Source Freshness panel.
- [ ] Add source-labeled forecast/rainfall layer and map legends.

**Deliverable:** Public-facing target platform **on Vercel**, initially using the weather source already validated.

## Phase 4 — Adaptive 2D/3D and geography UX

**Tasks**

- [ ] Add 2D/3D toggle and terrain with appropriate tile license.
- [ ] Add district extrusion for well-defined selectable metrics.
- [ ] Add zoom LOD, marker clustering, layer opacity and context rules.
- [ ] Add Basin mode when validated basin geometry exists.
- [ ] Benchmark WebGL/map render memory and low-powered/mobile devices.
- [ ] Optimize heavy boundary geometry with PMTiles or vector tiles as necessary.

**Deliverable:** Unified national-to-local adaptive **2D/3D** map.

## Phase 5 — Multi-source integration (incremental)

**Suggested onboarding order; actual order depends on verified access and quality:**

1. [ ] **RID** dam/reservoir products.
2. [ ] **TMD** official forecast, radar and warnings where authorized.
3. [ ] **HII/ThaiWater** rain/river gauges where accessible.
4. [ ] **GISTDA** satellite flood products with acquisition-time labeling.
5. [ ] Verified static basin/river layers, if absent.

Each adapter must pass a **source acceptance gate** (see Section 16). If an API is not accessible, hide that layer or mark it as planned; **do not fabricate demo values on production maps**.

**Deliverable:** Multiple independently sourced data layers on the **same map**.

## Phase 6 — Reliable release and quality hardening

**Tasks**

- [ ] End-to-end regression tests for national → region → province → district, plus Basin mode.
- [ ] Verify measurement unit, timestamps, stale/disconnected states and attribution.
- [ ] Verify failover for partial API failure and MongoDB read outage behavior.
- [ ] Audit database storage, indexes and retention; ensure bounded growth.
- [ ] Validate mobile layout, performance, accessibility and alert-like wording.
- [ ] Add monitoring, access controls, error handling and release rollback.
- [ ] Verify Vercel/atlas/provider plan eligibility for intended commercial/public use.

**Deliverable:** Stable Thailand Hazard Intelligence — Unified Monitoring v1.

## Future Optional Track — Not committed to MVP

- Sentinel-1 SAR custom flood extent extraction and external satellite validation.
- Hydrograph/routing graph, water arrival timing and hydraulic flood simulation.
- Historical event replay and hindcast validation lab.
- ML: river level forecasting, flood probability, historical analogues, GNN.
- Advanced scenario simulation and operational decision-support alert engine.
- PostGIS and dedicated geospatial services only when required by validated use cases/performance.

---

# 16. Source Acceptance and Definition of Done

## 16.1 Source acceptance gate

Before declaring any source integrated:

- [ ] Official endpoint or documented permitted access verified.
- [ ] Authentication/terms/quota/attribution/commercial constraints reviewed.
- [ ] Sample fetch tested end-to-end; no assumption from an API documentation page alone.
- [ ] Units, timezone, station/dam IDs and spatial coverage mapped.
- [ ] `observed_at` / `valid_time` and `fetched_at` distinguishable.
- [ ] Error rate, no-data semantics and publication delays evaluated.
- [ ] Atlas latest snapshot or tile URL strategy bounded and validated.
- [ ] UI tooltip, source attribution and age labels implemented.
- [ ] Failure fallback and source status tested.

## 16.2 MVP Definition of Done

- [ ] The **one main map** opens in Thailand National View.
- [ ] User can drill into Region → Province → District and back without changing operational pages.
- [ ] River Basin is selectable **when authoritative geometry is integrated**; otherwise clearly disabled/planned.
- [ ] Weather + eligible gauge/dam/warning/flood layers are accessible via one layer panel.
- [ ] Smart visibility prevents all detailed layers from overwhelming national view.
- [ ] 2D/3D terrain and truthful extrusion metrics work on supported devices.
- [ ] Clicking one area updates a unified Area Intelligence Panel.
- [ ] Every displayed data point discloses source, measurement unit and relevant timestamps.
- [ ] Forecast/radar/gauge/satellite observations are visually and semantically differentiated.
- [ ] GISTDA observations are **not** presented as live flood polygons.
- [ ] No unsupported flood probability/ETA/depth/risk score appears.
- [ ] MongoDB retains bounded latest records and last-good-data on failed ingestion.
- [ ] Website restart does not force nationwide API fetch.
- [ ] Source missing/stale/errors are visible, not mistaken for safe/no hazard.
- [ ] Data access and licensing are compatible with the actual deployment.
- [ ] Tested rollback path exists.

## 16.3 Verification tests

```text
tests/
├─ test_schema_semantics.py
├─ test_time_provenance.py
├─ test_location_identity.py
├─ test_data_source_normalization.py
├─ test_latest_snapshot_upsert.py
├─ test_snapshot_publish_atomicity.py
├─ test_missing_and_stale_data.py
├─ test_geo_integrity.py
├─ test_api_contracts.py
├─ test_layer_metadata.py
└─ e2e_national_to_local_drilldown.spec.ts
```

Test threshold boundaries where any source-specific severity classification is published. Favor automated contracts and real sample fixtures over visual-only checks.

---

# 17. Risks, Constraints and Trade-offs

| Risk | Consequence | Mitigation |
|---|---|---|
| Data from different sources are not simultaneous | False impression of a synchronized real-time map | Per-layer observation/valid times and age indicators |
| GISTDA products are delayed | Old flood polygon interpreted as live water | Date badge, source-specific legend and explicit satellite-observed label |
| Free API quota/license changes | Ingestion breaks or terms violated | Source registry, quotas, usage metrics, fallback and onboarding checks |
| Unknown ThaiWater/API permissions | Planned river layer unavailable | Gate source integration; never invent measurements |
| Daily-only radar/gauge refresh | Insufficient for rapid flood onset | Label it daily snapshot, optionally adopt finer source-specific cadence |
| District-level point forecast | Overclaims area-wide representativeness | Show grid/source resolution and aggregation method |
| Partial nationwide ETL update | Mixed-day map under one timestamp | Last-good or two-slot generation publishing |
| MongoDB read outage | No latest snapshot accessible | Show unavailable state; client cache when safe; plan operational recovery separately |
| Too many layers visible | Visual clutter, low performance | Zoom LOD, clustering, opacity, sensible defaults |
| 3D terrain/extrusion confuse interpretation | Tall polygon mistaken for flood depth | Explicit selected metric, legend and explanatory tooltip |
| Historical records removed too early | Loss of useful prior data | Review and explicit migration; do not delete automatically |

---

# 18. Implementation Backlog — Next Practical Steps

1. **Lock this V2 product direction** as the active roadmap; keep Master Plan as long-term vision.
2. Audit existing repo state and measure current MongoDB usage/record shape.
3. Create data contracts for Weather, Gauge, Dam, Satellite Product, Agency Warning, Area and Source Status.
4. Refactor Open-Meteo ETL to stable-ID latest snapshots with source/observation/forecast timestamps.
5. Set up Next.js + Vercel foundation and read-only MongoDB API layer.
6. Build National Overview and single-page map-first layout.
7. Implement Region → Province → District navigation with a separate River Basin path.
8. Introduce 2D/3D terrain, honest metric-based extrusion, legends and zoom LOD.
9. Integrate RID / TMD / HII / GISTDA **one by one after access and data quality verification**.
10. Add freshness, last-good-state, QC visibility and source metadata for every layer.
11. Test storage bounding, partial failures, mobile performance, license compliance and release gates.

## Decision rules for future work

- **Product UX remains unified:** add a new dataset as a layer/panel, not automatically as a new page.
- **Geographic drill-down is dual-mode:** administrative and hydrological, with no assumption that watersheds equal districts.
- **3D remains core:** no unnecessary flood-fluid simulation and no false physical meaning assigned to display heights.
- **MongoDB remains bounded:** latest valid source snapshots, with only explicit small rolling windows where needed.
- **Cost is free-first:** no unsupported assumption that a public service is free for all uses.
- **Data semantics before aesthetics:** observed / forecast / satellite / official warning must never be mixed.
- **ML, ETA, hindcast and replay remain research:** return only with a new explicit project decision.

---

# Appendix A — Legacy Repo Findings Carried Forward

The preceding roadmap reported the following code-level findings. They are treated as **prior review findings to reconfirm against the latest repository revision**, not as a new live audit performed while preparing this V2 document:

1. `app/weather.py::map_rain_level()` uses precipitation probability but labels it as rain intensity.
2. `etl/backfill.py` uses rainfall amounts and has overlapping historical processing paths.
3. Historical page's fetch button reportedly invokes the forecast ETL instead of historical backfill.
4. Location joins rely heavily on names instead of canonical administrative IDs.
5. The source GeoJSON files were previously reported near 24 MB (provinces) and 4.4 MB (districts).
6. Existing scheduled ingestion was set to morning and afternoon and uses a date-bearing upsert key, growing historical forecast documents across dates.

These do **not** justify continuing Streamlit as the target frontend. The target is Next.js/Vercel, while proven-good Python transformation/ingestion logic may be reused.

# Appendix B — Relationship to Previous Documents

| Document | Role after V2 |
|---|---|
| `THAILAND_HAZARD_INTELLIGENCE_MASTER_PLAN.md` | Keep as long-range digital twin / ML / flood-hydrology research vision |
| `WEATHER_API_REPO_UPDATE_ROADMAP.md` | Historical repo audit and stabilization proposal |
| `WEATHER_API_REPO_UPDATE_ROADMAP_LATEST.md` | V1 execution roadmap, **superseded by V2** on product, hosting, storage, ML and UI priorities |
| `THAILAND_HAZARD_INTELLIGENCE_ROADMAP_V2.md` | **Current active implementation roadmap** |

**Final direction:** **One unified Thailand map → progressive area and basin drill-down → combined multi-source intelligence → responsive 2D/3D visualization**, backed by Vercel/Next.js, scheduled source-specific ETL and **bounded MongoDB Latest Snapshots**. No mandatory ML pipeline or unbounded historical storage in the MVP.
