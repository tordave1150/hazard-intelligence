# Current execution scope — 28 October 2026

User-approved sequence: reconcile specification → Today with daily forecast access → four clock themes → quota/time-safe Today hourly forecast → evidence-supported cadence and offline shapefile work.

This supersedes sequencing/assumptions in the external `HAZARD_INTELLIGENCE_CODEX_EXECUTION_SPEC_2026-10-28.md`; the original file is unchanged. Baseline HEAD is `511d2ce`, with the preceding uncommitted GISTDA semantics/retention/capacity work preserved. No new source permission, acquisition date or deployment success is inferred from the document's Approved label.

## Decisions and acceptance

1. Today defaults to Situation Monitoring on the actual Bangkok calendar date, independently of available forecast dates. TMD/RID/GISTDA keep their own clocks. Today's daily forecast stays accessible; the next three calendar days offer daily forecast only. Missing dates remain visibly unavailable. Area and 2D/3D selection survive mode changes.
2. Dawn 05:00–06:59, Day 07:00–16:59, Dusk 17:00–18:29, Night 18:30–04:59 use the real Bangkok clock. One shared clock updates on mount/minute/resume. Hydration starts with a deterministic loading state. Only captured basemap layers are themed; scientific overlay colors, sources, listeners and camera are preserved. UI contrast follows the theme; no manual theme picker is added.
3. Hourly forecasts are an independent Today-only product with explicit preceding-hour precipitation/probability intervals and instant temperature. Daily weather retains its current four-period contract. Provider calls occur only in ingestion. Evaluate the user's suggested three-hour refresh against the combined daily/hourly/retry budget before enabling it; choose a more conservative interval if needed. Quota, freshness, rollover, last-good retention and rollback require tests.
4. GISTDA cadence separates query state from version evidence. Without a trusted product marker, record UNKNOWN_VERSION and never announce new imagery. A trial needs explicit start/end, bounded receipts and idempotent check IDs; no extra periodic provider requests are enabled without a useful marker and request-budget evidence.
5. Build a deterministic offline ZIP inspector with archive bounds, paired component validation, geometry/CRS/time classifications and safe output. Missing real ZIP/report means real-file results remain deferred. No source ZIP or derived geometry enters public paths, Atlas or the 1day layer.

## Delivery checks

- Exercise mode/date rollover and missing-data behavior, theme boundaries and map persistence, hourly contracts/budgets/intervals and failed publication, cadence state separation and archive attacks using synthetic fixtures.
- Run Python/frontend tests, TypeScript and build; verify browser/API/data flow and preserve precise distinction between local verification, provider evidence and deployed release.
- Retain the existing daily GISTDA publisher, pilot compatibility, source-specific last-good snapshots and credentials. Readiness for hourly/cadence/SHP is reported independently from Today/theme delivery.
- No user-requested task is considered complete merely because a disabled UI exists: explain the specific missing external evidence if a live product cannot be activated.


## Current delivery state

The Today/theme/hourly adapter, shared quota accounting, bounded publication diagnostics and offline inspector are implemented locally. The real ZIP was subsequently supplied and inspected; [findings](shapefile-inspection-2026-10-28.md) keep topology/provenance/time/reuse qualifications explicit. Browser and API evidence, the single real hourly provider check, remaining national-publication/deployment checks and rollback are recorded in the [local release candidate](current-execution-release-2026-10-28.md). There is no public real-SHP geometry or extra GISTDA polling schedule.
