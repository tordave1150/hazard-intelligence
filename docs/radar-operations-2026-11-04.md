# Radar continuity and upload budget

4 November 2026, Asia/Bangkok. This follow-up changes radar collection and operational reporting. Map fit, viewport, CSS and mobile layout are deferred at the user's request.

## Current policy

- Collect at UTC minutes 22/52 each hour (ICT has the same minute numbers), best-effort GitHub Actions. Sample only source timestamps at UTC minute 00/30. Keep at most seven images spanning three hours, anchored to the latest selected sample. Delayed collection never backfills the intervening quarter-hour images. Validate the original, unfiltered source manifest against the source clock before sampling.
- Seven frames are an upper bound, not a completeness promise. Preserve missing half-hour slots. Display the actual sample interval; old metadata without `sampling_minutes` remains readable as 15-minute data. The receiver applies half-hour sampling even to legacy queued producers. New producers wait for the sampling capability before sending the new optional metadata field.
- Latest displayed observation and capture time still jointly determine freshness (45/90-minute thresholds). Sampling does not change the clocks or extend the freshness thresholds. During the initial transition from a quarter-hour latest frame, retain the old pointer and success clock until the next nonregressing half-hour sample is available.
- Reuse known immutable time/hash URLs from the retained metadata generations. Keep active/previous generations and remove obsolete objects after promotion as before.
- Reserve a maximum of 1,800 application upload attempts over today and the previous 31 UTC dates. This covers at least 31 complete days. An initial 100 reservations leave conservative headroom for prior activity. Persist the whole candidate's new-file reservations under the existing publication lock before any PUT. Failed/uncertain attempts stay reserved; reused files need zero new reservations. Exhaustion or invalid ledger stops the batch before upload and retains the last complete pointer. The ledger contains at most 32 daily buckets.
- API health exposes reservation total/limit/remaining, not ledger details. These are **application reservations, not Vercel billing usage**. Other stores, dashboard listing, SDK/network retries and other consumers are not measured by this ledger. Normal half-hour cadence creates about 1,488 new timestamped files in 31 days plus initial backfill; pixel revisions, recovery and manual runs can use more. This reduces risk, not a guarantee that the account stays within every quota.
- The sender reports `capture_failed` only when source capture failed. Receiver, export and readiness failures no longer overwrite a specific `BLOB_UPLOAD`/`BLOB_BUDGET`/metadata failure with a generic capture notification.
- Radar GET metadata uses `no-store` for readiness/health, with the existing bounded server read cache. The next deployment's capability and quota/failure state cannot be served from an older CDN response.

[Vercel's current pricing](https://vercel.com/docs/vercel-blob/usage-and-pricing), checked 4 November, lists 2,000 included Hobby advanced operations; upload/copy/list/store creation consume them. Deleting files is free and reduces storage, not past upload operations. Hobby stops Blob access if limits are exceeded. No paid plan or subscription was activated.

## Store cleanup

The live store remains `hazard-radar-live` (`store_k3kJJWvSqH3gymwa`). Read-only metadata confirms the two unused setup stores contain zero objects/bytes and have no project connections:

- `hazard-radar` (`store_FCP0xEMvZd6uuteV`)
- `hazard-radar-production` (`store_5FlLNsjeVM4pkpWX`)

Deletion remains pending: the connected Vercel tools expose create/get, with no Blob-store deletion operation, and the available browser opens the Vercel login page. No extra store was created and the active connection was not changed.

## Verification

New tests cover fixed sampling and real gaps, sampled clocks, legacy readability, receiver capability, month-boundary budget retention, reserve-before-PUT ordering, reuse at the limit, exhaustion before upload, upload/metadata failures, pointer preservation, capture-failure stage and migration waiting. Full local checks: 300 Python tests (29 live HTTP tests skipped), 116 web tests, TypeScript and production build pass. The separate HTTP suite passes all 29 checks locally and all 29 against production.

Implementation commit `e0dda32d5e895f1ccc8f7a09cab13e0931d562ba` is served by the public production API; GitHub's Vercel commit status reports deployment completed. [Production receipt](radar-operations-production-2026-11-04.json) verifies all seven delivered PNGs against their declared hash, byte size, dimensions, CRC and decompressed stream (910,217 bytes total). Images cover 12:30–15:30 UTC / 19:30–22:30 ICT. Publication run 41862113424 logs `SUCCESS` with seven frames, health quality issues zero; four new-file reservations plus the 100-reservation initial headroom leave 1,696 of 1,800. Production browser confirms loaded imagery, cadence and budget text, with no console errors observed. Fit/mobile were not changed or reverified.

Downloadable CI job logs confirm 300 Python tests, 116 web tests, TypeScript and build completion. Run API snapshots continued reporting `queued`, inconsistent with those completed logs and the published run URL; the receipt preserves both observations rather than inventing an aggregate conclusion. Vercel deployment-list API returned 403 and alias inspection 404; production SHA, GitHub deployment status, job logs and delivered objects provide the release evidence. Server runtime logs were not available and no raw live Mongo/Blob retention audit was performed in this follow-up.

The pre-change GitHub run sample contains two successful **push** events (41840881308 and 41844595345) and no radar `schedule` event among the latest 50 repository runs. This does not establish recurring delivery or schedule drift. Retain that uncertainty until real schedule-event runs are observed. Missing runs and stale images remain visible through source health.

Workflow-state inspection confirms radar and the other eight workflow definitions are `active`; a separate sample of 30 schedule-event runs includes other collectors but no radar run. This still does not prove recurring radar execution. The follow-up publication above was triggered by a code push.

## 5 November schedule recheck

The [radar run 41920530553](https://github.com/tordave1150/hazard-intelligence/actions/runs/41920530553) is a completed successful **schedule** event, created 4 November 21:55:12 UTC / 5 November 04:55:12 ICT. This establishes that automatic scheduling has executed. At approximately 5 November 08:34 ICT, production still referenced that run and its latest image at 21:30 UTC / 04:30 ICT, correctly reporting STALE and hiding it. Therefore a continuous 30-minute delivery guarantee is not established. The code retains the configured best-effort schedule and quota/age protections; no paid scheduler or new external credential was activated.
