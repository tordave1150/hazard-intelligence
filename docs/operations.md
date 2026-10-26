# Operations and release runbook

## Local development

From the repository root, run `npm ci`. Create an isolated Python venv and install `tests/requirements.txt`. The Python runner does not auto-load `.env`; set credentials through the shell or an approved secret manager.

Real local previews (each source can be fetched independently):

```powershell
.\.venv\Scripts\python.exe -m pipelines.open_meteo.run --level all --export apps/web/data/local/weather.json
.\.venv\Scripts\python.exe -m pipelines.rid.run --export apps/web/data/local/dams.json
$env:HAZARD_LOCAL_SNAPSHOT='1'
npm run dev
```

Local snapshot files are ignored and never used by production, even if the local-preview flag is set. Production without MongoDB shows unavailable data. Reload snapshot reads stored data only; no visitor action runs nationwide ingestion.

## Existing Vercel project

User-selected target: **hazard-intelligence**. Set project Root Directory to `apps/web`; tracked `apps/web/vercel.json` installs/builds from the monorepo root. Use Node 22.x (or the project's eligible supported LTS version). Next.js target and lockfile versions are pinned.

The user confirmed this is a personal, non-commercial project shared publicly (2026-10-26). This matches the use category documented for Vercel Hobby and the Open-Meteo free API; retain attribution and stay within usage quotas. Re-evaluate the plans if the intended use changes. References: https://vercel.com/docs/plans/hobby and https://open-meteo.com/en/pricing.

Import the user-selected repository `tordave1150/hazard-intelligence` from Vercel's Add New → Project screen, and enable **Include source files outside of the Root Directory in the Build Step** because the app imports shared contracts. Creating a project requires an Owner or Member role, or a Developer role with the Create Project extended permission. Reference: https://vercel.com/docs/projects/managing-projects and https://vercel.com/docs/monorepos/monorepo-faq.

Set `MONGODB_URI` and `MONGODB_DB_NAME` in the project's server environment. Use an Atlas database user restricted to read access for Vercel; never prefix credentials with `NEXT_PUBLIC_`. Do not store source keys in the browser. Atlas network access must explicitly permit the selected runtime's egress path. Choose static egress/private networking where available; do not automatically open Atlas to all IPs.

The website also accepts `MONGODB_URL`, matching Vercel's storage-integration output when Custom Prefix is `MONGODB`. `MONGODB_URI` takes precedence if both are present. This alias is for the server reader; the independent Python/Actions ingestion still uses its separately configured `MONGODB_URI` writer credential.

Production is deployed at https://hazard-intelligence-lime.vercel.app/. GitHub ingestion secrets are configured, the live audit passed, and manual run 40257438014 published the first complete snapshot on 2026-10-26 at 09:15:36 Asia/Bangkok. The public API and browser confirmed MongoDB storage, 1,005 valid points, FRESH, SUCCESS and four forecast days. The connected Vercel plugin still cannot see the project in its selected team (`team_V0dZUHXqiEyo9Tu4vJN3gCoO`); resolve connector visibility before platform changes and do not create another project. There is no installed/authenticated Vercel CLI fallback.

## Scheduled ingestion

`.github/workflows/etl.yml` runs once daily at 01:00 UTC / 08:00 Asia/Bangkok, or manually. It needs Actions secrets `MONGODB_URI` (write-capable, restricted to the latest collections), `MONGODB_DB_NAME`, and optionally `OPEN_METEO_API_KEY` for commercial/customer access. No workflow writes the Git repository, appends legacy history, or depends on Vercel uptime. Concurrency is serialized with cancellation disabled.

In the new repository, the job explicitly skips ingestion with a notice until both MongoDB secrets are configured. Secrets are not copied from the legacy repository. Add them in GitHub repository Settings → Secrets and variables → Actions; add the server's read-only MongoDB credential separately in Vercel project Settings → Environment Variables. Never paste credentials into an issue, PR, chat or source file.

Once configured, each run executes the read-only `scripts.mongo_admin audit` before fetching or publishing. A failed audit stops the job. The checkout and Python setup actions are pinned to verified official commit SHAs. First-run instructions for Atlas users and repository secrets are in `VERCEL_SETUP_TH.md`.

Active workflows use official action commits whose manifests specify Node.js 24. The app build itself still targets Node.js 22. Pipeline requirements declare dnspython explicitly for SRV connections rather than relying on the removed pymongo[srv] extra. Successful ingestion clears the previous error_summary; the reader masks historical error summaries when the current status is not FAILED.

```powershell
.\.venv\Scripts\python.exe -m pipelines.open_meteo.run --level all --publish
```

Publication requires `--level all`; a province-only export cannot replace national Atlas coverage. Four daily variables × four forecast days for 1,005 locations are fetched in groups of 25, pausing three seconds per group. Coordinate accounting still applies; batching is not a quota bypass. Retry 429/5xx responses with capped backoff and Retry-After. Raw response/key/URI is not logged. Failed runs exit nonzero and retain last-success metadata and last-good published data.

If transient transport, rate-limit or upstream failures leave gaps, the collector keeps successful batches and retries only failed batches in at most two recovery passes, each after a 60-second cooldown. Normal batch pacing still applies. Recovery does not relax schema, units, time, coverage or matching-period checks. Logs expose fixed reason codes and HTTP status only. A re-run from GitHub's failed-job action uses the original run commit; use a fresh manual run on main to exercise newly committed recovery code.

The current GitHub connector can read workflow status/logs but its re-run mutation returned 403 `Resource not accessible by integration`. Until Actions write access is available, start a fresh run through the repository's Actions → Latest weather snapshot → Run workflow → main. The agent can then inspect its results through the read connector without retrieving secrets.

## Audit and migration

Before first write, run `python -m scripts.mongo_admin audit` with an authorized account. This reports collection counts, indexes, data/storage/index sizes without exposing documents or credentials. The first live workflow audit passed and reported an empty database. Post-publication measurements and deployed restart/failover checks still need to be captured.

No migration deletes legacy collections. The new publishers write only weather_latest, dam_latest, snapshot_control, source_status and etl_locks. Existing forecasts and weather_historical remain preserved. The old Streamlit app is a reference; its probability labels are corrected, UI-triggered ingestion is retired, and the original version is recoverable at the baseline tag. Legacy CLI backfill is unsupported and not scheduled.

## RID daily-storage ingestion

`.github/workflows/rid.yml` is **Latest RID reservoir report**. It runs independently at 01:15 UTC / 08:15 Asia/Bangkok or via Run workflow → main. It uses the existing repository secrets `MONGODB_URI` and `MONGODB_DB_NAME=weather_db`; no new provider credential is needed for this public documented GET. The writer must have permission for `dam_latest` and the shared control/status/lock collections in that database. Do not broaden permissions if the existing database-scoped readWrite user already supplies this.

The sequence is configuration check → read-only database audit → one 35-dam report fetch/validation/publication → read-only `verify` → actual post-write storage audit. The verifier checks both products' active coverage, schema, identity indexes and two-slot bounds, while allowing an unpublished product to remain UNAVAILABLE. It never creates indexes. The publisher creates its own required indexes only when publishing. RID and weather use separate concurrency groups and product locks; neither fetch is part of a website request.

```powershell
.\.venv\Scripts\python.exe -m pipelines.rid.run --publish
.\.venv\Scripts\python.exe -m scripts.mongo_admin verify
.\.venv\Scripts\python.exe -m scripts.mongo_admin rollback --source rid
```

Rollback requires an intact previous generation. For a confirmed stopped RID writer use `unlock --source rid --stopped-run-token <exact-token>` under the same stopped-process requirements as weather. Do not run recovery or rollback merely to test production without an agreed maintenance window.

The accepted storage product excludes inflow/outflow. Its report date is independent of the forecast date; exact observation time is unavailable. Freshness cannot be reset by retrieving an old report. See [RID acceptance](rid-acceptance-2026-10-26.md) for measurement, coordinate and reuse evidence. The live page shows awaiting publication until the first complete Atlas report exists; local captures are never a production fallback.

## Rollback and interrupted runs

For a frontend release, use Vercel's prior deployment promotion/rollback. For data, use `python -m scripts.mongo_admin rollback`; the command verifies that the recorded previous run still exists before switching pointers. Edge/server caches may retain the old response for up to roughly three minutes.

If a worker is killed during publication, the non-expiring product lock intentionally blocks another writer. Confirm that the process/workflow is stopped, inspect `etl_locks` with an authorized database console, then use `python -m scripts.mongo_admin unlock --stopped-run-token <exact-token>`. Never unlock a running writer. A failed inactive slot may invalidate the prior rollback generation; active data stays readable. Back up Atlas independently: A/B slots are not disaster recovery.

## Checks

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp artifacts/pytest-check
npm run typecheck
npm run test:web
npm run build
$env:HAZARD_TEST_URL='http://127.0.0.1:3000'
.\.venv\Scripts\python.exe -m pytest tests/test_api_smoke.py -q --basetemp artifacts/pytest-http
```

Create the `artifacts` parent before using a new `--basetemp` path. Final local verification also started the production server with an intentionally unreachable local MongoDB URI and confirmed a sanitized unavailable response with no local-data fallback.

Browser regression specification: `apps/web/tests/e2e_national_to_local_drilldown.spec.ts`. It was verified through browser interaction during development; the specification itself has not been executed by an automated Playwright runner. Physical mobile/GPU benchmarks and live Atlas failover remain release gates.

## Source onboarding

For RID, TMD, HII/ThaiWater and GISTDA, record official documented endpoint, auth, permission, commercial/redistribution rights, quota, real sample fetch, IDs, units, timestamps, latency and coverage. Add provider transform, validation/publication and failure tests; only then activate a layer. Official website links alone are not integration evidence. Basin data requires independently verified geometry and spatial intersections.

Review Open-Meteo API eligibility, Vercel plan eligibility and Atlas capacity for intended public/commercial use. The free Open-Meteo endpoint is non-commercial. Data attribution does not grant commercial free-endpoint access.
