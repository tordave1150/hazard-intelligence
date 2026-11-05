# Radar recovery and lossless GISTDA capacity

5 November 2026, Asia/Bangkok. This follow-up addresses recurring Radar delivery and GISTDA storage headroom. Map fit, mobile/layout, new radar-derived numerical products and new paid services are outside this increment.

## Radar diagnosis and recovery

The Radar workflow was active. Its latest pre-change run, `41920530553`, was a successful schedule event at 4 November 21:55 UTC; no newer Radar jobs appeared even though other collector schedules had completed. Production retained the 21:30 UTC image and correctly hid it as stale. The observed break was before job creation, rather than a demonstrated image capture or Blob failure. [GitHub documents that schedule events can be delayed or dropped](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule); these observations alone do not identify GitHub's internal cause.

The existing `radar.yml` now checks at minutes 7/22/37/52 and also receives completion events from four existing trusted workflows: TMD CAP, HII stations, hourly forecast and application checks. Recovery checks out current reviewed `main`, accepts only the same repository's main-branch push/schedule/manual upstream events, and does not consume upstream artifacts or upstream executable code. OIDC still requires the exact Radar workflow path, repository ID, main ref, GitHub-hosted runner, audience/signature and short token lifetime; `workflow_run` is the only added event. No new long-lived key is introduced.

Before source capture, a public API check compares the last published observation with the eligible fixed half-hour sample, allowing twelve minutes for source delivery. Recent attempts have a ten-minute cooldown. A current sample skips capture and publication entirely: it does not renew source query or image clocks, spend Blob upload reservations, or create duplicate source observations. Readiness failures allow an actual capture attempt; invalid/stale captures and existing quota/lock protections still reject publication. The producer waits for the compatible recovery receiver before using the recovery event.

Source registry text now distinguishes original quarter-hour source image times, half-hour stored samples and quarter-hour due checks. Stored sequences remain at most seven frames over three hours. Successful recovery is not a promise of uninterrupted thirty-minute delivery: all wakeups still depend on GitHub Actions events. There is no new paid scheduler or unrelated account.

## GISTDA measured capacity and encoding

The [read-only pre-change report](flood-capacity-before-2026-11-05.json) measured 162,865,856 bytes of compressed flood objects. Mongo reported 186,130,035 data bytes plus 2,490,368 index bytes, below the 419,430,400-byte application ceiling. This is an operational guard, not a discovered billing-plan limit.

All active chunks were decoded, re-encoded and compared before enabling the new representation. The complete 7-day product measured 33,298,089 → 29,627,835 bytes; 30 days measured 129,567,767 → 112,912,694 bytes. The latter is approximately 123.57 → 107.68 MiB, increasing headroom below the unchanged 128 MiB per-product guard. Whole-object and whole-database guards remain 320/400 MiB. The report includes actual usage/headroom and a conservative fully-changed-next-query projection rather than claiming unlimited capacity.

`msgpack-gzip-v1` stores the same normalized records as MessagePack with double-precision floating-point values, then deterministic gzip. It does not round coordinates, simplify geometry, merge distinct provider records, infer dates or introduce area/depth metrics. The new reader accepts this encoding and the existing JSON `gzip-v1`; producer readiness explicitly checks the supported encoding list. Each delivered object remains limited to 1 MiB decompressed and 100 records, hash-bound, schema-checked and administratively validated. A Python-produced golden fixture checks JavaScript decoding of double precision and signed zero.

The bounded collector uses the new representation for future complete national queries. A reviewed `repack_thailand_windows` request re-encodes existing 3/7/30-day products without provider calls. The original feed, retrieval/response/ingestion timestamps, row identities, index ordering and prior distinct query remain unchanged. Repacking records storage maintenance separately; it does not create a new satellite observation or claim a fresh API query. A generation check before promotion rejects source changes during migration.

Complete new objects precede the atomic pointer change. Old representations remain readable for a 120-second grace, exceeding the thirty-second manifest cache; they are protected from eviction throughout that grace. Query history omits duplicate replaced representations. The Action waits 130 seconds before pruning expired managed representations and then deep-verifies payloads and measures capacity. Legacy source collections and the current/previous distinct queries remain protected. Migration failure before promotion leaves the original pointer intact.

Future immutable object writes use batches of at most twenty chunks (at most 20 MiB), reducing database round trips. Partial batch failures are cleaned as unreferenced objects before releasing the lock; they do not promote an incomplete product or change the active pointer. This batching change is tested separately from the already-started maintenance run.

## Operating commands

Read-only capacity and full lossless comparison:

```text
python -m scripts.mongo_admin verify --deep-flood --flood-capacity --measure-flood
```

Explicit rollback selects a product independently:

```text
python -m scripts.mongo_admin rollback --source gistda --flood-window 7days
```

`repack-flood` waits for the compatible reader and repacks the active queries. `prune-flood` only cleans expired managed representations under the shared exact-token lock. Normal cron/manual publication remains separate national 3/7/30-day queries with the default map window at three days.

## Verification

The [production receipt](data-continuity-capacity-production-2026-11-05.json) records completed migration, pruning, complete payload audit, actual capacity, public API and browser verification. [Maintenance run 41955814865](https://github.com/tordave1150/hazard-intelligence/actions/runs/41955814865) succeeded with provider collection skipped. All ten active products verified after migration, including all 2,010 active GISTDA chunks. Counts remain 0 / 50,219 / 132,962 and original source query clocks remain unchanged. Public API comparisons of 203 records across three selected area queries have identical normalized record hashes before/after. All seven original Radar PNGs passed hash, byte-length, dimensions, CRC and decompression checks (569,346 bytes total).

[Automatic recovery run 41957477978](https://github.com/tordave1150/hazard-intelligence/actions/runs/41957477978), event `workflow_run`, published a new seven-frame sequence with latest observation 5 November 02:30 UTC / 09:30 ICT, retrieved 02:48 UTC. Its due decision was true and publication succeeded. Six already-verified images were reused; the new image additionally passed the PNG checks. Reservations increased only from 118 to 119, leaving 1,681/1,800. A subsequent [recovery check](https://github.com/tordave1150/hazard-intelligence/actions/runs/41957891893) skipped capture because that sample was already published, preserving its clocks and reservation balance.

Final [CI checks](https://github.com/tordave1150/hazard-intelligence/actions/runs/41957779200) passed 336 Python tests (29 opt-in HTTP checks skipped), 126 web tests, TypeScript and production build. All 29 separate production HTTP checks passed. Local checks cover both formats above 20,000 records, three generations across all three windows, cross-window object reuse, exact numeric round trips, mixed codecs/corruption, cached old pages during migration grace, retained distinct-query rollback, partial batch writes, storage failure before promotion and read-only measurements. Radar checks cover current-sample skip, cooldown, stale/missing sample recovery and exact-workflow authentication. Production browser verified loaded Radar imagery, complete 592-record selected-area geometry with the bounded list, the migrated 30-day national summary and original retrieval clocks; console errors were absent. Temporary QA area selection does not establish a preferred location.

## Capacity interpretation after pruning

Compressed flood objects now occupy **142,540,529 bytes**, a reduction of **20,325,327 bytes / 19.38 MiB**. The object guard has 193,003,791 bytes of headroom. At this measured state, a second fully changed run of the same compressed sizes would occupy 285,081,058 object bytes, below 335,544,320. This is an application-budget projection; later growth and additional protected distinct queries can still reject a candidate.

Zero added bytes applies to replaying byte-identical chunks. A newly fetched query can partition records differently or contain changed features, even with the same encoding; future deduplication is not predicted. The current reporting field makes that assumption explicit; earlier receipts preserve their original field labels as captured evidence.

The final read-only capacity run `41957779160` reports 165,823,062 data bytes plus 2,895,872 index bytes. Allocated collection storage remains **475,820,032 bytes** after the temporary copies. The optional reusable-storage metric was not returned and is recorded as null. MongoDB's [dbStats definition](https://www.mongodb.com/docs/manual/reference/command/dbstats/) includes free allocated collection space in `storageSize`; deleting documents does not immediately shrink that allocation. Application headroom is explicitly labelled as a data-plus-index operational guard. Actual disk availability and billing-plan limits remain undiscovered. No compaction or paid plan change was performed.
