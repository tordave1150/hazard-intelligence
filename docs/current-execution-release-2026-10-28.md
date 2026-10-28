# Today, clock themes and bounded forecast tooling — release record

Approved scope: [current execution specification](execution-spec-current.md). The user explicitly authorized uploading the 49 changed files to `tordave1150/hazard-intelligence` and deploying `hazard-intelligence-lime.vercel.app`. Commit `db0b1fd82826c7162f8e96606e4ca988c55119f1` is now deployed to production. National hourly publication has not been run as part of this release; its reader handles the pending product explicitly. The earlier national GISTDA release remains the source-data baseline.

## Product behavior

- Today is the real Asia/Bangkok calendar date even if the weather snapshot lacks that date. It defaults to Situation Monitoring with source-specific warnings/reports, honest rain/gauge unavailability, and access to today's daily and hourly forecasts. The next three calendar dates use daily forecast only. Missing forecast dates are explicitly unavailable. Administrative selection, layer toggles and 2D/3D survive mode changes.
- Four clock themes use Dawn 05:00, Day 07:00, Dusk 17:00, Night 18:30 boundaries. One clock refreshes each minute and on tab focus/resume. Rendering starts with a deterministic loading state to avoid a server/client date mismatch. The basemap layer IDs are captured before custom hazard sources are added; only those base layers receive paint changes. Metric scales, CAP/GISTDA colors, terrain and camera are preserved. Theme does not depend on forecast selection.
- `/api/hourly` reads a separate bounded `today_hourly` product. No browser interaction calls a provider or starts ingestion. Hourly is loaded only on opt-in, and API responses return one selected interval per point plus shared interval metadata rather than repeating 24 hours for every point. At ICT rollover yesterday's hourly data supplies no Today intervals; a delayed first publication is disclosed. A partly elapsed current hour is labelled as a full-hour forecast, not an amount for its remaining minutes.

## Hourly contract and request budget

`HourlyForecast` holds 24 explicit one-hour intervals for the retrieval day's Bangkok calendar, mm/1h precipitation, % precipitation probability and °C temperature at the interval end. Provider request labels run from 01:00 Today through 00:00 Tomorrow to cover the full day: precipitation/probability describe the preceding hour. Model issue time stays null. Hourly and daily use separate contracts, collections, pointers, status and rollback.

Cadence: **every four hours**, targets **00:17, 04:17, 08:17, 12:17, 16:17, 20:17 ICT** (`17 1,5,9,13,17,21 * * *` UTC). At 1,005 points the base hourly workload is 6,030 coordinate units/day; adding daily gives 7,035 before retries. The proposed three-hour cadence would use 9,045 before retries and exceeds the chosen 9,000-unit guard. This is a conservative budgeting model for short best-match requests with fewer than ten variables; provider billing/egress conditions still apply.

Daily/hourly reserve before every HTTP attempt, including failed retries, against the **same** rolling CAS ledger in `provider_request_budget`: 500 coordinate units/60 seconds, 4,500/hour, 9,000/24 hours. The one-document ledger prunes events older than 24h and holds at most 9,000 events. Budget errors prevent further HTTP attempts and partial promotion. Exports use a process-local budget, so manual exports do not claim cross-process/global accounting. Both collectors pace 25-point batches, reject redirects and cap real response bodies at 2 MiB/60 seconds.

Hourly publishes 1,005 records atomically into `weather_hourly_latest`, bounded to 2,010 across A/B slots; any failed/incomplete batch retains the previous generation. Reader validates canonical point identities and all periods. Snapshot freshness is fresh through six hours, delayed through ten, then stale; failure downgrades freshness, and previous-day data is stale regardless of retrieval age. This describes snapshot age, not a known model run age.

Actual single-point provider check: on **2026-10-28T15:18:43.159664Z / 22:18:43 ICT**, the requested Bangkok representative point returned all 24 intervals, from 2026-10-27T17:00Z through 2026-10-28T17:00Z. It passed normalization/units/time checks. This is **one real point**, not a completed national hourly publication or verified production readback. Sanitized receipt: ignored `artifacts/hourly-provider-check-2026-10-28.json`.

References: [Open-Meteo parameters and preceding-hour definitions](https://open-meteo.com/en/docs), [free-access terms](https://open-meteo.com/en/terms), [weighted request accounting](https://open-meteo.com/en/pricing), [MapLibre paint properties](https://maplibre.org/maplibre-gl-js/docs/API/classes/Map/#setpaintproperty).

## GISTDA publication diagnostics

The daily publisher remains at 09:27 ICT. Its final diagnostic step records existing publication/query evidence with **no extra GISTDA request**. Query state (empty/nonempty/failed/not checked) is separate from version state. Actual provider marker semantics are unverified, so active receipts remain UNKNOWN_VERSION. No new-image notification or publication-hour inference is implemented from response clocks or feature counts.

Trial interval is 2026-10-28T00:00Z through 2026-11-11T00:00Z, then recording stops. At most 56 redacted receipts occupy one source-specific journal; expiry is 14 days after the trial ends. Job-start bounds prevent an older successful snapshot from becoming evidence that a failed current job checked the provider. Extra four-per-day polling remains disabled pending a useful trusted version marker and quota evidence. This is a publication diagnostic trial, not a claim that release-cadence discovery is complete.

## Offline shapefile inspection

Install optional local dependencies with `python -m pip install -r scripts/requirements-shapefile.txt`, then:

```powershell
python -m scripts.inspect_flood_shapefile 'C:\external\source.zip' --output artifacts/shapefile-report.json
```

It never extracts archive members or exports geometry. It checks archive paths, duplicates, symlinks/encryption, compression/entry/byte bounds, one SHP/SHX/DBF/PRJ set, record offsets/counts, encoding, polygon topology, exact duplicates, null/zero field counts, CRS and lineage distinctions, administrative-code relationships, and a 120-second/5-million-position limit. Output files must be new files under ignored `artifacts/`. Raw attributes, creator identifiers and URLs are excluded. Source permissions, acquisition/publication time and tambon identity remain unknown. Boundary overlap and spatial accuracy are explicitly not checked; no area total, water depth or impact statistic is inferred.

The user subsequently supplied the real ZIP. [Offline inspection](shapefile-inspection-2026-10-28.md) reproduced 1,306 polygons / 2,742,629 positions, 32 province / 188 district / 1,306 tambon codes, final CRS 4326 and lineage CRS 32647. OGC/GEOS validation reported 876 Ring Self-intersections; Esri validation was not run and no repair was applied. The original hash was unchanged. The source/provenance report and display/redistribution rights remain unverified. No real ZIP-derived geometry, tiling deployment or fallback into `1day` is enabled.

## Operation and rollback

- National hourly writer: `python -m pipelines.open_meteo.hourly --publish`, existing server-side MongoDB/Open-Meteo secrets, `hourly.yml` on main. Missing access/configuration fails without replacing data.
- Validation: `python -m scripts.mongo_admin verify` includes hourly. Rollback: `python -m scripts.mongo_admin rollback --source hourly`; stopped-run unlock uses `--source hourly` and the exact lock token.
- Cadence summary: `python -m scripts.gistda_cadence --summary`. Manual recording also requires an explicit `--attempt-after` UTC job-start bound.
- Deploy the compatible readers before running the hourly publisher. A frontend rollback can ignore the extra product without deleting it. Pause hourly ingestion before rolling back to a daily collector that predates shared budget accounting. Do not run production rollback merely to test it.
- Remaining live checks: complete national hourly fetch/publication, Atlas quota ledger/index/retention checks and deployed API/browser readback. Deployment/CI success is not inferred from local tests. GISTDA scientific/version/reuse gaps and real-SHP provenance remain separate.


## Verification evidence

- Full offline Python suite: **232 passed, 19 skipped** using `.venv/Scripts/python.exe -m pytest -q --basetemp artifacts/pytest-delivery-final` (8.06 seconds). The 19 opt-in production HTTP tests were not run in this change.
- Frontend: **34 tests**, TypeScript and the final production build passed. Tests cover Bangkok rollover, all four theme boundaries, hourly/daily scales, unknown/failure states and pending-style handling. Final route output contains `/api/hourly` and no temporary theme QA route.
- Browser/API: Today default, Today daily/hourly and future daily-only behavior were inspected. Bangkok/3D persisted across date selection; Ongkharak/3D and selected GISTDA overlay persisted through Dawn/Day/Dusk/Night with a temporary local injected clock. A pending-style race found during hot reload was fixed and regression-tested; the fresh browser session then reported no warning/error logs.
- Mobile 390×844 browser: document client/scroll widths both **375 px**, no horizontal page overflow. Hourly opens its panel first, the drawer closes, and Escape restores source-dialog focus to its opener. This is responsive browser verification, not a physical-device/GPU benchmark.
- Synthetic national API check: **1,005 points**, one interval per point, 24 shared available windows, **794,824 bytes**. District filtering returned one point; invalid time/area returned 400/404; hourly source status reflected the snapshot. Only local synthetic data was involved.
- Temporary hourly/flood fixtures and the local theme-control route/component were hash-checked and removed, the owned server/tab was stopped/closed and viewport overrides reset. Existing local source snapshots and original external documents/ZIP were not changed. At completion of this local QA stage, no new Atlas data, remote commit, deployment or provider message had been created. The later connected deployment is recorded below.
- Local proof: `artifacts/today-theme-night-review.jpg`, `theme-{dawn,day,dusk,night}-qa.jpg`, `today-hourly-mobile-qa.jpg`, `current-execution-local-api-check.json`, and `hourly-provider-check-2026-10-28.json`. Temporary clock buttons exist only in QA captures, not in the delivered website.


## Main changed paths by phase

- Specification/release: `docs/execution-spec-current.md`, this release record, roadmap, data contract, source registry and operations.
- Today: `apps/web/components/dashboard.tsx`, `apps/web/lib/dashboard-mode.ts`.
- Themes: `components/time-theme.tsx`, `lib/map-theme.ts`, `components/map/map-view.tsx`, `app/layout.tsx`, `app/globals.css` under `apps/web`.
- Hourly: `pipelines/open_meteo/{hourly,budget,client,run}.py`, `packages/contracts/schema.json`, `scripts/mongo_admin.py`, `.github/workflows/hourly.yml`, and web hourly contract/reader/API/panel helpers.
- Diagnostics: `scripts/gistda_cadence.py`, existing GISTDA workflow, `scripts/inspect_flood_shapefile.py` and its optional dependencies; real-SHP findings are documented separately.
- Regression: `tests/test_hourly.py`, `tests/test_offline_tools.py`, `apps/web/tests/dashboard.test.ts`, with prior GISTDA regression edits preserved.

## Connected rollout — 28 October 2026, approximately 23:24 ICT

- Source commit: [`db0b1fd`](https://github.com/tordave1150/hazard-intelligence/commit/db0b1fd82826c7162f8e96606e4ca988c55119f1). Branch CI [40725143151](https://github.com/tordave1150/hazard-intelligence/actions/runs/40725143151) passed both Python and web jobs, including TypeScript, frontend tests and production build, before main was fast-forwarded. The GitHub connector lacked write permission; the existing authenticated Git connection completed the authorized push.
- Vercel production deployment `dpl_8Mt6MzwzeMHqCxUdaejeF4t3YC5N` is READY, targets this exact source commit and owns the existing public aliases, including [the live website](https://hazard-intelligence-lime.vercel.app/). Build duration was approximately 35 seconds; aliasError is null. Previous production deployment `dpl_E9CsTW3wwvn1Ygu1T1nLTufVRNnA` remains the recorded rollback baseline.
- Real-clock browser check: the live URL displays **NIGHT theme · Bangkok clock**, with dark interface and dark basemap. Today's daily forecast remains accessible (103.6 mm/24h national maximum from the existing snapshot). Selecting 29 October retains Night and 3D. The browser reported no warning/error console entries during this check. Proof: ignored `artifacts/today-night-production-2026-10-28.jpg`.
- All **19 production HTTP checks passed** in 25.77 seconds. Four additional hourly endpoint checks passed: normal read 200, invalid parameter 400, unknown area 404 and POST 405. The reader reports Mongo storage, no read error, zero records and zero available intervals. The live hourly panel explicitly says no applicable hourly forecast for today; no national hourly publication is claimed. Receipts: ignored `artifacts/today-themes-production-http.xml` and `today-night-production-hourly-check.json`.
- Vercel runtime-log access returned 403, so an infrastructure error-log scan could not be completed. HTTP/browser verification passed; this permission failure is not evidence of zero runtime errors. No protection, permissions or credentials were changed. No synthetic data or ZIP-derived geometry was published.
- Live visual QA also found that the enabled metric selector retained a dark daytime text color on its dark surface. The small follow-up uses the existing light ink token for Night/Dusk; daytime styles and forecast values are unchanged. The final production receipt records the follow-up deployment and computed color verification.
