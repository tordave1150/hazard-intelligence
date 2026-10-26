# Data contract 2.0

The active machine-readable contract is `packages/contracts/schema.json`, generated reproducibly by `python scripts/create_contracts.py`. Python ingestion and Next.js reads both validate against it. JSON Schema draft 2020-12 defines Area, Forecast, WeatherObservation, WaterGauge, DamObservation, SatelliteFloodProduct, AgencyWarning and SourceStatus. Forecast and DamObservation have accepted adapters; the other product contracts remain reserved. Defining a contract does not activate a provider.

## Identity

`TH` is national; `TH-R-{upstream reg_royin}` identifies a versioned project region. `TH-P-{two-digit pro_code}` and `TH-D-{four-digit amp_code}` preserve published administrative codes. Names are display attributes. District IDs must start with their parent province code. IDs are unique and parent relationships are checked. Independent current DOPA registry verification is still pending; do not claim a completed authoritative audit.

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

Satellite contracts require acquisition time, retrieval time, processing method and licensed external product reference. No raster scenes are stored in MongoDB. Gauge contracts preserve station datum and published threshold definitions. Agency warnings preserve issuer categories and effective/expiry windows. No composite flood-risk score, flood ETA or depth is defined.
