# Data contract 2.0

The active machine-readable contract is `packages/contracts/schema.json`, generated reproducibly by `python scripts/create_contracts.py`. Python ingestion and Next.js reads both validate against it. JSON Schema draft 2020-12 defines Area, Forecast, WeatherObservation, WaterGauge, DamObservation, SatelliteFloodProduct, AgencyWarning and SourceStatus. Forecast, DamObservation and AgencyWarning/WarningFeed have accepted adapters; other product contracts remain reserved. Defining a contract does not activate a provider.

## Identity

`TH` is national; `TH-R-{upstream reg_royin}` identifies a versioned project region. `TH-P-{two-digit code}` and `TH-D-{four-digit code}` identify administrative areas. Names are display attributes. District IDs must start with their parent province code. IDs are unique and parent relationships are checked. The [DOPA comparison](dopa-geography-review-2026-10-26.md) matches all 77 province/928 district codes and Thai names to the official downloadable directory dated 2023-09-01; later registry changes and legal geometry remain unverified.

The versioned manifest corrects the boundary source's Wiang Kao code `4026` to official `4029` and six Thai labels. Old stored weather snapshots are read compatibly only at that exact original representative point; responses expose the applied mapping in `identity_migrations`. Forecast values/coordinates/times remain unchanged. New ingestion requires the corrected ID and rejects old IDs or collisions. No database migration or backfill is required.

## Forecast semantics

One document per location contains four daily `valid_periods`, separate rainfall in mm/24h and probability in percent, null-preserving temperature values and explicit UTC start/end instants for Bangkok local days. Source response units, timezone, contiguous dates, numeric ranges and complete location coverage are checked. Entirely empty weather records fail. Partially missing variables retain `null` and get `quality_status=partial`.

`forecast_reference_time` is null: the selected endpoint does not supply a reliable issuance timestamp. Never substitute retrieval time as model issuance. `fetched_at` is when the response arrived; `ingested_at` is when normalization occurred. `point` is the requested representative interior point; `model_point` is the actual returned grid coordinate. Polygon colors and extrusion represent that point, not an area average.

## Bounded publication

`DamObservation` represents RID's accepted `daily_dam_storage` product. Canonical `RID-DAM-{source ID}` identities and whitelisted published coordinates are frozen in `apps/web/data/rid-dams.json`. `normal_capacity_mcm`, `maximum_capacity_mcm` and `storage_volume_mcm` are million m³; `storage_pct` uses normal capacity and has no 100% ceiling. Nulls are preserved. `report_date` has calendar-date precision, `observed_at` is null, and `time_precision` is `date`. No flow rate or observation instant is inferred. Source, metadata and license links are mandatory and checked against the accepted product.

`dam_latest` has a unique `(source_id, product_id, slot, dam_id)` index. Its 35-report complete generation requires one report date and at most 70 stored documents across A/B slots. RID's control/status/lock key is `rid:daily_dam_storage`, separate from `open_meteo:daily_forecast`. The read-only `scripts.mongo_admin verify` checks both active products, schema, coverage, indexes and retention.

`weather_latest` unique index: `(source_id, product_id, slot, location_id)`. Full national scope is 1,005 forecast points, with at most 2,010 documents after repeated publication. No date appears in the unique key. `snapshot_control` contains one active pointer per source/product, generation UUID, record count, revision and the previous pointer. `source_status` holds one latest run-health document; it is an internal ETL health shape, distinct from the public SourceStatus contract. `etl_locks` holds at most one active lock per product.

Only complete, unique, valid and period-consistent batches promote. A failed fetch/export/publication leaves the active pointer unchanged. Inactive slot writes complete and are counted before atomic pointer replacement. Writers serialize using a unique lock with no unsafe automatic expiry. Hard-killed workers require explicit recovery after confirming termination. Reader queries include both slot and run UUID, verify count and retry pointer races. Database outages return `UNAVAILABLE`, never fabricated zeros or an automatic provider fetch.

## Freshness

Forecast freshness uses the older of first valid start and retrieval time: ≤30h FRESH, ≤48h DELAYED, otherwise STALE. Missing timestamps are UNKNOWN; absent data is UNAVAILABLE. Stale records remain readable with age indicators and lose map thematic colors. Gauge/satellite observation ages need separate source-specific rules when accepted; do not reuse forecast retrieval age for them.

RID freshness additionally checks report calendar age: today's report retrieved within 30 hours is FRESH; at most two calendar days old and retrieved within 48 hours is DELAYED; otherwise STALE. Future/invalid timestamps are UNKNOWN. A newly retrieved old report cannot become FRESH. Changing the selected forecast date does not change the RID report date.

Satellite contracts preserve verified acquisition time when supplied, retrieval time, processing method and the external product reference with applicable reuse qualifications. Missing acquisition stays null; a product-window label or retrieval time cannot fill it. Acceptance is specific to the displayed use case; unknown area units exclude area metrics without blocking a bounded geometry adapter. No raster scenes are stored in MongoDB. Gauge contracts preserve station datum and published threshold definitions. Agency warnings preserve issuer categories and effective/expiry windows. No composite flood-risk score, flood ETA or depth is defined.

## GISTDA retrospective 1day query

`GistdaNationalFloodFeed` wraps the complete bounded unfiltered provider query, with `product_window=1day` meaning the previous one-day window (ย้อนหลัง 1 วัน). A query on 28 October may return the 27 October product; no product date is calculated from the query clock. `observed_at=null` and `observation_time_status=NOT_SUPPLIED` preserve the missing exact acquisition metadata. `response_at`, `fetched_at` and `ingested_at` remain distinct UTC instants. Query freshness cannot establish observation freshness.

Only checked geometry, generated IDs, canonical administrative references and fixed query/source metadata are persisted. Raw provider properties/links and unverified area/exposure values are excluded. National storage is bounded to two 4-MiB envelopes; pilot storage is separate. Oversized/incomplete/failed refreshes retain the last complete generation and expose a fixed human-readable failure category. No partial snapshot is promoted. See [current acceptance scope, retention and scaling limits](gistda-integration-acceptance-2026-10-28.md).


## TMD CAP warnings

`AgencyWarning` preserves the TMD sender/identifier, Actual/Public status, Alert/Update/Cancel type, exact references, CAP issue/effective/expiry instants, agency classification, plain source text, explicit province codes and original polygon rings. Missing expiry is null. `WarningFeed` wraps complete item accounting and at most 50 messages, allowing an explicitly empty valid feed. RSS assembly and retrieval times are separate from CAP message issuance.

`agency_warning_latest` uses unique `(source_id, product_id, slot, snapshot_id)` keys, with snapshot_id=latest and at most two complete envelopes of up to 2 MiB each. Its independent control/status/lock key is `tmd:cap_warnings`. Completeness means processing of the feed's listed items, not complete national coverage. Public API responses separate envelope metadata from records to avoid duplicate payloads and expose message_states computed with global update/cancel references.

Feed freshness is FRESH through two hours, DELAYED through six, then STALE, using the older of assembly/retrieval. Failure downgrades a fresh prior feed to DELAYED. Message lifecycle is independent: current validity window, upcoming, expired, cancelled, superseded or time unknown. Only currently valid messages from a FRESH feed receive current thematic outlines. Explicit historical inspection uses gray reference outlines; a fresh retrieval never extends expiry or implies safe conditions.

## Today hourly forecast

`HourlyForecast` is separate from `Forecast`: `product_id=today_hourly`, `forecast_date` is the Bangkok retrieval day, 24 explicit one-hour `valid_hours`, preceding-hour mm/1h/probability, and temperature at each interval end. Issue time is null. National coverage is 1,005 canonical representative points; `weather_hourly_latest` keeps at most 2,010 across independent A/B slots. Missing/partial refreshes retain the previous generation; yesterday is never relabelled Today. See [cadence, quota ledger and rollback](current-execution-release-2026-10-28.md).
