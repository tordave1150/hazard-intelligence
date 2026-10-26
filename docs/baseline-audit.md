# Baseline audit — 2026-10-25 Asia/Bangkok

Repository: `tordave1150/weather_api`. Audited commit: `b4b038c82681717d1f0bb94800d8c949c5036c5c`. Local safety tag: `baseline/roadmap-v2-2026-10-25`. Implementation branch: `codex/hazard-intelligence-v2`. No original collection or deployment was deleted.

| Finding | Confirmed evidence | Treatment |
|---|---|---|
| Probability labeled rainfall intensity | `map_rain_level(80)` previously returned `Very Heavy Rain` | Corrected to `80-100% chance`; V2 independently separates amount/probability |
| Historical refresh routes to forecasts | `app/historical.py` called `etl/fetch_weather.py --round afternoon` | Retired UI-triggered ingestion; regression checks prevent forecast ETL call |
| Forecast accumulation | `etl/fetch_weather.py` upsert identity included daily `date` | New bounded collections with source/product/slot/location identity; legacy collections preserved |
| UI executes national ETL | Legacy forecast Refresh used subprocess | Disabled legacy Refresh; Next.js has read-only APIs and reloads stored snapshots |
| Different location counts | Forecast inputs: 77 provinces / 913 districts; old geometry: 78 provinces / 928 districts | Versioned source geometry: 77/928; canonical code joins replace ambiguous name joins |
| Heavy province asset | Old province GeoJSON: 25,076,655 bytes; districts: 4,676,385 bytes | Display province file: 863,760 bytes; districts split into 77 lazy-loaded files; raw inputs preserved |
| Duplicate history transformations | `etl/backfill.py` has two transformation paths with different thresholds and unflushed final docs in main | Historical ETL retained as unsupported reference and excluded from new scheduled path; no automatic migration/deletion |

Live Atlas collection counts, indexes, data/storage size and current deployment behavior could not be measured without a configured database connection. The read-only `python -m scripts.mongo_admin audit` command is supplied for that environment. This document does not invent baseline counts or claim the original deployment was tested.

The new real national ETL was exercised independently of the web frontend. Its successful local export contains 1,005 records and four daily windows, about 1.39 MB of JSON. Map geometry validation checked feature validity, unique IDs, hierarchy and representative-point coverage; build report records hashes and maximum simplification area change (~2.20%).
