# Execution status — Roadmap V2

Updated: 2026-10-26, Asia/Bangkok. This is an execution record, not a claim that every roadmap phase is production-complete.

## Implemented and verified locally

- Preserved original commit with a baseline tag, and saved the original README.
- Canonical source-coded geography: Thailand, 6 regions, 77 provinces, 928 districts. Pinned raw boundaries, reproducible build, checksums, valid simplified polygons and per-province district loading.
- Shared contracts for forecasts, observations, gauges, dams, warnings, satellite products, areas and status.
- Open-Meteo adapter: bounded retries, unit/time/coverage validation, null preservation, explicit grid-point representativeness, separate volume/probability, no invented model issue time.
- A real nationwide sample fetch successfully normalized **1,005/1,005** locations and four daily periods. It is an ignored local preview file, not production demo data.
- Bounded A/B MongoDB publication code, serialized writers, atomic promotion, last-good retention, retrying readers, rollback verification and explicit crashed-lock recovery. Unit tests use mongomock; no live Atlas write has occurred.
- Daily GitHub Actions ingestion definition, independent of frontend availability. It has not run in the remote repository yet.
- Next.js map with national → region → province → district navigation, Thai/English search, breadcrumbs, area evidence, source freshness, date/metric switching, opacity, export and unavailable states.
- MapLibre/deck.gl 2D, terrain-aware native 3D and truthful metric extrusion. Browser verification found and repaired terrain occlusion and competing camera transitions.
- Responsive layer/area drawers, source dialog with Escape/focus handling, legal/attribution and methodology pages.
- Legacy probability label correction and retirement of the historical forecast-refresh misroute.
- Published the reviewed project to the user-selected `tordave1150/hazard-intelligence` repository as initial `main` commit `380ec66be7656f99f51946a08515d90af2080663`. The destination was verified empty. The legacy remote/history remain local; the new repository starts from the reviewed current tree. Initial GitHub CI run 40248139281 completed both Python and web jobs successfully.
- Final production build and TypeScript checks passed. **44 Python/HTTP tests + 6 frontend tests passed**, including HTTP checks against the production server. A deliberately unreachable local MongoDB address returned `UNAVAILABLE` and zero records with sanitized errors, even while the local-preview flag was enabled. The active snapshot reader did not fall back to bundled/local weather. Live Atlas failover still requires access.
- Browser checked national/region/province/district navigation, Mae Sai local panel, 3D terrain/extrusion, probability legend, Thai search, mobile drawers, source status and Escape close. No map console errors were observed. At mobile viewport 390px, document content width was 375px (no horizontal overflow). Physical-device/GPU memory benchmarking remains unperformed.

## Current external blockers and unfinished release work

1. **Deployment completed; connector visibility unresolved:** GitHub's Vercel status confirms successful deployment of commit `468a5c49183d9d1c5c0c501011a59e022510feaa`. The user supplied the production URL https://hazard-intelligence-lime.vercel.app/; the page and its API were verified publicly. The connector's selected team (`team_V0dZUHXqiEyo9Tu4vJN3gCoO`) still returns 404 for this project/deployment and an empty project search. The GitHub deployment status links to the intended team/project, so this is a connector visibility issue, not a reason to create another project. The in-app dashboard requires login. Platform environment names, region and rollback settings remain uninspected. No authenticated CLI fallback is available locally.
2. **Atlas connected to the website; ingestion not configured:** production `/api/overview` returned HTTP 200, `storage: mongo`, `error: null`, `records: []`, `status: null`, `freshness: UNAVAILABLE`. The server successfully read MongoDB but found no published snapshot. The user confirmed that GitHub Actions MongoDB secrets have not yet been configured and requested setup instructions. Live collection audit, index/storage measurements, first national publication and live restart/failover remain pending. No legacy data has been touched.
3. **Provider acceptance:** documented RID API was probed successfully (35 records), but coordinates, flow-unit/time semantics and reuse terms are unresolved. TMD registration, agency-specific ThaiWater access and GISTDA key/license/acquisition acceptance remain pending. Their layers and read APIs clearly report unavailable/planned. See `source-acceptance.md` for official references and actual probe evidence. Authoritative basin geometry is not integrated.
4. **Geographic authority:** source codes and spatial consistency are verified against pinned published geometry; a current authoritative DOPA registry audit is pending.
5. **Release qualification:** actual intended-use plan eligibility, physical-device performance and deployed rollback verification remain outstanding. The automated Playwright specification is saved; it has not been run by a Playwright runner. Current browser checks were performed through the connected browser.
6. **GitHub publication completed:** the previous push to `weather_api` was rejected by automatic approval review and never occurred. The user then explicitly selected `https://github.com/tordave1150/hazard-intelligence.git` in reply to the publishing question. That authorized public destination was verified empty and received the reviewed initial `main` tree without a force push. No publishing approval remains pending for this selected repository. No draft PR was needed to initialize an empty repository; existing project files were not overwritten.

## Shutdown condition

The user requested `shutdown /s /t 120` only after all tasks, tests and file operations are complete, with no unresolved errors or pending approvals. The external blockers above mean that condition is **not satisfied**. Do not schedule shutdown while they remain.

See `operations.md` for exact continuation commands, source acceptance steps, deployment settings and rollback/recovery procedures.

The staged-file audit found no secrets, local snapshots, dependency directories, Vercel credentials or runtime artifacts. Git whitespace checks passed after text normalization; raw boundary bytes remain preserved by `.gitattributes`.

## Continuation after Vercel installation

Confirmed installation and rechecked the explicitly selected team/project. Vercel remains connected, but hazard-intelligence still returns 404; the earlier 403 creation denial has not been resolved. No deployment, public push, authentication change or shutdown was attempted during this continuation. The runtime source registry now reflects the official RID probe, TMD registration, agency-specific ThaiWater access and GISTDA's unspecified-license/key requirements.

The metadata update passed TypeScript, the production build, 30 offline Python tests and 6 frontend tests. The 14 running-server HTTP tests were skipped in that continuation because verification servers had been stopped; all 14 passed in the earlier complete production-server check recorded above. No new server or database mutation was needed for that metadata-only change.

## MongoDB integration continuation

The website accepts the integration-style `MONGODB_URL` as an alternative to `MONGODB_URI`; explicit URI takes precedence. This keeps the screenshot's `MONGODB` custom prefix usable without moving credentials into code or chat. The independent Python ingestion still uses its separately configured writer URI. TypeScript, the production build and all 6 frontend tests passed after this change. A production-server request with only a deliberately unreachable local `MONGODB_URL` selected MongoDB storage, returned `UNAVAILABLE`, zero records and a sanitized error, and did not use the local preview even with its flag enabled. The verification server was stopped; no real Atlas credential or database was used.

MongoDB's native-integration documentation states that a Vercel team installation maps to a new Atlas organization and the initial installer becomes its Organization Owner. The screenshot does not identify the actual Atlas login email or organization ID; these must be checked through Open in MongoDB Atlas. See `VERCEL_SETUP_TH.md`.

## Production verification and first-ingestion preparation

The live page displays the map and explicitly reports no published weather data. The 14 HTTP contract checks passed against production after correcting an origin-only cache assertion: Vercel consumes and removes `s-maxage` and `stale-while-revalidate` from client responses, as documented at https://vercel.com/docs/caching/cdn-cache. A production response confirmed `Cache-Control: public`, `x-vercel-cache: HIT` and age 34 seconds. This was a test expectation issue; the application's CDN policy was retained. The full suite passed 44 Python/HTTP tests, 6 frontend tests, TypeScript and the production build.

The map caption now distinguishes unavailable and unknown-time snapshots from stale snapshots. ETL now audits collection/index/storage metadata before attempting fetch or publication; a failing audit prevents writes. Checkout and Python setup actions were pinned to the official tag commit SHAs and checkout does not persist its token. User action remains necessary to create/configure the dedicated database writer and the two GitHub Actions secrets before the first run. No secret was retrieved or entered by the agent.
