# Execution status — Roadmap V2

Updated: 2026-10-26, Asia/Bangkok. This is an execution record, not a claim that every roadmap phase is production-complete.

## Implemented and verified locally

- Preserved original commit with a baseline tag, and saved the original README.
- Canonical source-coded geography: Thailand, 6 regions, 77 provinces, 928 districts. Pinned raw boundaries, reproducible build, checksums, valid simplified polygons and per-province district loading.
- Shared contracts for forecasts, observations, gauges, dams, warnings, satellite products, areas and status.
- Open-Meteo adapter: bounded retries, unit/time/coverage validation, null preservation, explicit grid-point representativeness, separate volume/probability, no invented model issue time.
- A real nationwide sample fetch successfully normalized **1,005/1,005** locations and four daily periods. It is an ignored local preview file, not production demo data.
- Bounded A/B MongoDB publication code, serialized writers, atomic promotion, last-good retention, retrying readers, rollback verification and explicit crashed-lock recovery. The first incomplete live runs were rejected; a fresh run on the recovery code subsequently published all 1,005 records to Atlas and the production website read them successfully.
- Daily GitHub Actions ingestion, independent of frontend availability. Manual workflow run 40257438014 on `16675c2` succeeded and completed national publication; failures and recovery are recorded below.
- Next.js map with national → region → province → district navigation, Thai/English search, breadcrumbs, area evidence, source freshness, date/metric switching, opacity, export and unavailable states.
- MapLibre/deck.gl 2D, terrain-aware native 3D and truthful metric extrusion. Browser verification found and repaired terrain occlusion and competing camera transitions.
- Responsive layer/area drawers, source dialog with Escape/focus handling, legal/attribution and methodology pages.
- Legacy probability label correction and retirement of the historical forecast-refresh misroute.
- Published the reviewed project to the user-selected `tordave1150/hazard-intelligence` repository as initial `main` commit `380ec66be7656f99f51946a08515d90af2080663`. The destination was verified empty. The legacy remote/history remain local; the new repository starts from the reviewed current tree. Initial GitHub CI run 40248139281 completed both Python and web jobs successfully.
- Final production build and TypeScript checks passed. **44 Python/HTTP tests + 6 frontend tests passed**, including HTTP checks against the production server. A deliberately unreachable local MongoDB address returned `UNAVAILABLE` and zero records with sanitized errors, even while the local-preview flag was enabled. The active snapshot reader did not fall back to bundled/local weather. Live Atlas failover still requires access.
- Browser checked national/region/province/district navigation, Mae Sai local panel, 3D terrain/extrusion, probability legend, Thai search, mobile drawers, source status and Escape close. No map console errors were observed. At mobile viewport 390px, document content width was 375px (no horizontal overflow). Physical-device/GPU memory benchmarking remains unperformed.

## Current external blockers and unfinished release work

1. **Deployment completed; connector visibility unresolved:** GitHub's Vercel status confirms successful deployment of the RID implementation commit `3a498a8cd615e6408f667bcfbcc236ae685af048`. The user supplied the production URL https://hazard-intelligence-lime.vercel.app/; the page and its API were verified publicly. The connector's selected team (`team_V0dZUHXqiEyo9Tu4vJN3gCoO`) still returns 404 for this project/deployment and an empty project search. The GitHub deployment status links to the intended team/project, so this is a connector visibility issue, not a reason to create another project. The in-app dashboard requires login. Platform environment names, region and rollback settings remain uninspected. No authenticated CLI fallback is available locally.
2. **Atlas publication completed; remaining operational qualification:** run 40257438014 on `16675c2` published 1,005/1,005 records. Production `/api/overview` reports MongoDB storage, FRESH, SUCCESS, completeness 1.0, no read error and forecast dates 2026-10-26 through 2026-10-29. All 1,005 production records passed the shared Python schema and complete-coverage checks; model issue times remain null because the provider does not supply them. Last success is 2026-10-26 09:15:36 Asia/Bangkok. Post-publication storage/index measurements were captured by RID run 40287126263; its read-only verifier passed weather and RID coverage, schemas, indexes and retention. Live database restart/failover remains pending; legacy data has not been touched.
3. **Provider acceptance:** RID daily storage is now accepted after matching 35 official point coordinates, capacity/percentage definitions, date-only precision and the linked DGA catalog reuse terms. Its adapter, independent API and map layer are implemented and tested; Atlas run 40287126263 subsequently published and verified all 35 reports. Flow fields remain excluded pending exact definitions. TMD registration, agency-specific ThaiWater access and GISTDA key/license/acquisition acceptance remain pending. Their layers and read APIs clearly report unavailable/planned. See `source-acceptance.md` for official references and actual probe evidence. Authoritative basin geometry is not integrated.
4. **Geographic authority:** source codes and spatial consistency are verified against pinned published geometry; a current authoritative DOPA registry audit is pending.
5. **Release qualification:** the user confirmed personal, publicly shared, non-commercial use, matching the documented use category for Vercel Hobby and Open-Meteo Free. Actual usage must remain within each plan's limits. Physical-device performance and deployed rollback verification remain outstanding. The automated Playwright specification is saved; it has not been run by a Playwright runner. Current browser checks were performed through the connected browser.
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

## First live ETL failure and bounded recovery

Run https://github.com/tordave1150/hazard-intelligence/actions/runs/40254094317 on `b48493d` passed audit and retrieved 980/1,005 locations. Its single failed batch began at offset 275. The old log recorded only RuntimeError, so it cannot establish whether the request failed because of transport, 429 or 5xx. The run's final ValueError is the complete-coverage gate, not evidence of a MongoDB connection failure. No partial snapshot was promoted. A targeted real request for those same 25 locations later validated all four daily periods successfully.

The collector now retains good batches and makes at most two recovery passes for transient request failures, with a 60-second cooldown and the same three-second batch pacing. Permanent HTTP errors and invalid semantic data are not retried by recovery; complete coverage and matching periods are still required before publication. Safe diagnostics report only reason codes and HTTP status, never provider bodies, URLs or credentials. Regression coverage verifies recovery without duplicate/refetched good batches, exhausted recovery rejection, permanent/invalid data rejection and credential-safe exceptions. All 51 Python/HTTP tests passed, including the production HTTP checks. A GitHub re-run of the existing failed run retains that run's original commit; it is a production retry, while CI separately verifies the new recovery code on main.

The fix was published as `28d8aea4c4cf7c32453b44a714a930679d263a6f` and its Vercel deployment completed successfully. The connector's failed-job re-run request was rejected with HTTP 403 `Resource not accessible by integration`; no new ETL attempt started through it. A fresh manual Run workflow on main is requested so that the recovery code is actually exercised. Secrets remain configured and must not be re-entered in chat.

The user subsequently started attempt 2 of the existing run, which retains `b48493d` (before the recovery fix). It also failed with 980/1,005 locations, this time at offset 100 rather than 275. It does not exercise the new recovery code. Its pre-fetch audit passed: one source-status document, 828 data bytes, 36,864 storage bytes and 36,864 index bytes; no forecast snapshot existed. A fresh Run workflow on main was requested with the distinction from Re-run jobs explained. CI passed for both the recovery code commit `28d8aea` and the documentation continuation `e21cfa9`. The user also confirmed personal/non-commercial public use; official use-category references were rechecked at https://vercel.com/docs/plans/hobby and https://open-meteo.com/en/pricing on 2026-10-26. Data attribution and API quotas still apply.

## First complete production snapshot — 2026-10-26

Fresh manual run https://github.com/tordave1150/hazard-intelligence/actions/runs/40257438014 on `16675c2932d959922f743b8d8ad5c46cecdcbb0e` completed successfully. Its log ends with SUCCESS and record_count 1005; no batch failure or recovery-pass event occurred in this particular run. The public API independently returned 1,005 records, FRESH, SUCCESS and completeness 1.0 for 26–29 October. All records passed shared validation and canonical coverage checks, with zero partial records and 1,005 null provider model-issue times. Browser verification on the deployed site passed national → Northern → Chiang Rai → Mae Sai → national navigation, live values, 2D/3D terrain and metric extrusion. Screenshot evidence is ignored under artifacts/production-fresh-national.png and artifacts/production-mae-sai-3d.png.

The successful run still carried an old failure's error_summary in source_status because success used only $set. Success publication now unsets that historical error field; the web reader also suppresses a stale failure summary on non-FAILED status for compatibility with already-published data. A regression test covers failure-to-success status cleanup after actual mock publication. All 52 Python/HTTP tests, 6 frontend tests, TypeScript and the production build passed after this cleanup.

The run's Node.js 20 action warning was traced to checkout v4 and setup-python v5. Both workflows now pin reviewed official checkout v7.0.1, setup-python v7.1.0 and setup-node v7.1.0 commits where applicable; their action manifests specify Node.js 24. The obsolete pymongo[srv] extra warning is removed from the active pipeline requirements by declaring pymongo and dnspython explicitly. These maintenance updates do not change the daily/manual ingestion cadence.

The separate GitHub notice announces the ubuntu-latest migration to Ubuntu 26; it is not a data or authentication failure. Both workflows now explicitly use the supported ubuntu-24.04 runner to keep the reviewed OS consistent rather than changing under a moving label. The warning and notice remain historical annotations on the completed run; they are not erased retroactively.

## RID daily storage development — 2026-10-26

Implemented the accepted initial `rid:daily_dam_storage` product: one documented GET, 35 source-matched identities and published coordinates, explicit normal versus maximum capacity, null preservation and percentages above 100 when valid. Report dates retain date-only precision (`observed_at=null`); inflow/outflow are excluded. The [acceptance record](rid-acceptance-2026-10-26.md) documents official endpoint, metadata provenance, license-scope interpretation and exclusions. A real CLI export normalized all 35 reports for 26 October; ignored local files are never a production fallback.

The independent publisher uses `dam_latest` (at most 70 documents), with its own A/B control/status/lock keys. Weather's 1,005-point contract and 2,010-document bound remain intact. The new read-only `mongo_admin verify` checks active coverage, schema, unique identity indexes and retention for both products without creating indexes or modifying data. Weather and RID workflows run separately and both verify the database after publication; RID additionally captures actual post-write storage. Existing database-scoped repository secrets are reused.

The map now has a switchable RID layer, national region-count groups, individual dam points in regional/zoomed views and detailed daily-storage cards. All values retain source, units and dates. Forecast date selection defaults to today's available window, preserves an explicit selection and identifies the selected date. Changing the weather date does not alter RID's report date. Browser checks passed national group to regional points, marker selection, the real 109.91% report, 2D/3D and the independent dates. At a 390px mobile viewport the document content width and scroll width both measured 375px; the dam drawer closes and reopens from a marker. This is a responsive-browser check, not a physical-device/GPU benchmark.

The complete local suite passed **70 Python/HTTP tests and 8 frontend tests**. TypeScript passed after the marker grouping change. The production build passed. A production server with a deliberately unreachable MongoDB address returned UNAVAILABLE, zero weather/dam records and sanitized errors for both products and their source status, even with the local-preview flag enabled. Owned test servers were stopped. Production deployment evidence follows after publication. The local preview screenshot is ignored under `artifacts/rid-preview-eastern-3d.png`.

The user started the first **Latest RID reservoir report** run on main, 40287126263, and all steps succeeded. The GitHub connector still has no Actions write permission; no new secret was needed. TMD/HII/GISTDA acceptance, basin geometry and the broader release-qualification gates remain outstanding. The shutdown condition remains unsatisfied.


## First RID production publication and actual Atlas audit

Implementation commit `3a498a8cd615e6408f667bcfbcc236ae685af048` passed GitHub CI run https://github.com/tordave1150/hazard-intelligence/actions/runs/40286989242 and Vercel deployed it successfully. The user's fresh RID run https://github.com/tordave1150/hazard-intelligence/actions/runs/40287126263 succeeded on that commit. Source status reports 35/35, completeness 1.0, SUCCESS, report date 26 October 2026 and last success 14:39:55 Asia/Bangkok. All 35 records read back from the production API passed shared validation, exact metadata identities and date-only precision. Production reports MongoDB storage, FRESH and no read error for both products. All 1,005 weather records were identical to the pre-RID capture.

The post-write read-only audit captured these point-in-time sizes; storage engines may update allocation later:

| Collection | Documents | Data bytes | Storage bytes | Index bytes |
|---|---:|---:|---:|---:|
| weather_latest | 2,010 | 2,882,032 | 667,648 | 286,720 |
| dam_latest | 35 | 38,013 | 4,096 | 12,288 |
| snapshot_control | 2 | 804 | 36,864 | 36,864 |
| source_status | 2 | 996 | 36,864 | 36,864 |
| etl_locks | 0 | 0 | 32,768 | 32,768 |

The verifier found 1,005 active weather records within the 2,010-document bound and 35 active dam records within the 70-document bound, with the required unique identity indexes present for each. Weather collection document counts and all three size figures were unchanged before and after RID publication. No legacy collection was present in this target audit or modified by the new publisher. The RID job emitted no warning/error annotations in its captured log. The complete suite also passed against the deployed app: 70 Python/HTTP checks.


Production browser verification passed the national region-count groups, Eastern regional points, marker selection, correct storage/capacity details, the real >100% value, date-only observation precision, 2D/3D terrain and independent 27 October forecast versus 26 October RID report. No browser warning/error log was captured during that session. Screenshot evidence is ignored under `artifacts/production-rid-eastern-3d.png`. The production read API returned the same 1,005 weather records captured before RID publication. Temporary local servers were stopped and the browser viewport override was reset.

This completes the initial RID daily-storage delivery and its first production publication. It does not complete TMD/HII/GISTDA access/product acceptance, authoritative basin geometry, the independent DOPA registry audit, physical-device/GPU benchmarking or live deployed rollback/failover qualification. The user's all-work-complete shutdown condition is therefore still not met; no shutdown was initiated.
