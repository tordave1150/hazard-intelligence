# Province comparison, measured rain and basin context

Thailand-wide defaults, 30 October 2026 (Asia/Bangkok). No preferred province, district, station allowlist or local collector was added. Administrative geography remains unchanged.

## Update continuity

Public GitHub run history showed successful TMD and hourly collectors, followed by missing scheduled executions; source_status also showed SUCCESS rather than a provider failure. GitHub documents that schedule events can be delayed or dropped under load: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule

TMD now checks at UTC minutes 11/41 and publishes only after one hour since success or a failed attempt. Hourly forecasts check at minute 23 each hour and publish after four hours, a failed attempt, or a new Bangkok day. `scripts.refresh_guard` reads existing status; skipped ticks never update ingestion timestamps. Explicit reviewed push requests and manual refreshes can force collection. Existing publication locks, concurrency groups and shared Open-Meteo rolling budgets remain in force. More scheduler opportunities improve catch-up but do not guarantee execution times or an external scheduling SLA.

The first guard run exposed an incorrect Python MongoDB timeout keyword; it was corrected to `max_time_ms`, with a scheduled-path test added. Recovery TMD run 41085668604 and hourly run 41085668454 succeeded. These successful runs, rather than a change to freshness thresholds, restored current source data.

## 77-province comparison

The existing map opens an optional comparison panel with search, region filter, current CAP message filter, data-gap/quality filter and source-specific sorting. A single `/api/provinces/overview` request returns all 77 rows and per-source clocks, approximately 42 KB in the reviewed preview. It does not perform 77 geometry requests. GISTDA counts reuse one pinned generation's validated ID/administrative index; no polygon payload is sent to the table.

Today rainfall forecasts use the province representative point. Station counts, connected RID reservoir counts, CAP message validity and satellite footprint counts stay separate. Measured zero, zero returned rows and unavailable products differ. Missing rain values and invalid CAP intervals remain visible; HII's unknown observation timezone is a source-wide qualification rather than a fabricated current age. Sorting never averages station MSL elevations or derives a flood-risk score.

## Observed rain

The endpoint `https://api-v3.thaiwater.net/api/v1/thaiwater30/public/rain_24h` was observed in the official ThaiWater portal application and fetched without credentials. The review returned 4,811 unique automatic station IDs: 4,808 canonical Thai rows across all 77 provinces and three foreign-code rows. These are response counts, not permanent required inventories.

The separate `ThaiWaterRainFeed` contract and `rain_gauge_latest` collection retain mm/24h and mm/1h as reported, original wall timestamps, null observation UTC and null UTC accumulation-window bounds. Negative, non-finite and missing rain are flagged rather than converted to zero. District association requires a unique exact Thai district-name match inside the supplied province. The review matched 4,804 district names; unmatched districts stay unassigned. Rain values do not become forecast rain or area averages.

Each of water level and rain has independent A/B slots and health status, with a maximum two documents per product. The HII workflow makes one bounded public request per product every two hours. A failed water-level step does not suppress the configured rain step. Browser polling reads an approximately 5 KB rain summary first; complete station rows download only when needed and are reused while fetched_at is unchanged. No website-embedded keys or arbitrary user-provided provider URLs are accepted. Attribution identifies HII / ThaiWater and original measuring agencies; no unrestricted live-product licence or undocumented quota is asserted.

Public source times still omit timezone. The reviewed portal code and general standards did not establish a documented timezone binding for these live fields. Unknown observation age therefore remains explicit; UTC conversion and current observation freshness are not claimed.

## 22-basin context

Source: [DDPM GIS published 22-basin layer](https://gis-portal.disaster.go.th/arcgis/rest/services/MapDX/DPM_TH_Hydrology/MapServer/6), EPSG:4326, with [ONWR government catalog reference](https://gdcatalog.go.th/th/dataset/gdpublish-dataset-32-0113). The catalog specifies public data with no access condition but no licence; no unrestricted reuse licence is asserted. The reviewed raw response hash and transformation receipt are in `basin-context-source-2026-10-30.json`.

`scripts.build_basin_context` validates exactly 22 unique source codes. Precision-induced degenerate/self-touching geometry was repaired with polygon-only `make_valid`; every relative source area change was below 1e-6 (actual maximum below 7e-11). Display geometry uses topology-preserving 0.002-degree simplification. Matching uses 0.0002-degree simplification, an inward 0.0005-degree margin and a check that the membership core does not extend outside the repaired source. Border/coastal or multiple matches stay unassigned. All 35 connected RID points matched one basin interior in this review. Dynamic HII points are matched server-side; membership geometry is never shipped in client bundles.

The separate Basin selector shows HII points and RID dams within the selected basin in 2D/3D. Source basin codes are retained as their own namespace; administrative codes are not replaced. No river-network connectivity, flow direction or upstream/downstream ranking is inferred. Basin forecasts, TMD province-warning counts and GISTDA administrative memberships are explicitly unsupported in basin queries; zero is not substituted for those unsupported products.

## Verification

Local checks: 265 Python tests, 66 web tests, TypeScript and production build passed. The 24 local HTTP checks passed. Browser preview confirmed 77 table rows, current-warning and quality-gap filters, mobile province selection, 4,808 rain stations, separate 24h/1h units, basin selection, and a Ping basin response with 76 water stations and three RID dams. Production deployment, publication and browser evidence are recorded after the live cycle below.
