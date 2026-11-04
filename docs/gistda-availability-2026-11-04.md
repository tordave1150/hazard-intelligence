# GISTDA flood availability and intermittent observation coverage

Checked 4 November 2026. [Machine evidence](gistda-availability-2026-11-04.json) records the production snapshot, six daily runs and the bounded current window comparison. This document distinguishes verified behavior from recommended future work; only the diagnostic improvement is implemented in this increment.

## Verified cause of the empty map

The application is still querying the complete unfiltered national **3days** product. Production has a successful complete response at **09:30 UTC / 16:30 ICT on 4 November**, with **zero returned features**. The API and publication are functioning for that response. Observation/acquisition time remains null.

| Scheduled query day | Result | Provider features published |
| --- | --- | ---: |
| 30 October | Success | 803 |
| 31 October | Success | 597 |
| 1 November | Success, empty provider collection | 0 |
| 2 November | Success, empty provider collection | 0 |
| 3 November | Collection rejected: `NATIONAL_FEATURE_BUDGET_EXCEEDED` | None; last complete generation retained |
| 4 November | Success, empty provider collection | 0 |

The [3 November run](https://github.com/tordave1150/hazard-intelligence/actions/runs/41613330980) encountered a provider-reported count **above 20,000**, the configured cap, and stopped before complete geometry collection. This is a separate application capacity problem. It is not evidence that the provider lacked data that day. The [4 November run](https://github.com/tordave1150/hazard-intelligence/actions/runs/41807947529) successfully published zero from the source. Neither condition proves why a satellite did or did not observe a particular place.

The publisher, schemas, server index, API pagination and browser assembly all enforce related bounds: 20,000 features, 64 MiB source bytes, 32 MiB normalized feed, two million coordinate positions, 512 chunks and a 600-second collection deadline. Changing one constant cannot make the larger products work end to end. A/B retains two latest complete generations; it is not a dated 30-day observation archive. Consecutive successful empty responses can replace the earlier nonempty generations.

## Current source comparison

[Diagnostic run 41865924093](https://github.com/tordave1150/hazard-intelligence/actions/runs/41865924093) made exactly four independent, unfiltered, one-page requests using the existing Actions credential in the API-Key header. No source links/assets were followed, no raw properties or credentials were logged, and no geometry was published.

| Retrospective source product | HTTP | `numberMatched` | Response time UTC, 4 November |
| --- | ---: | ---: | --- |
| 1day | 200 | 0 | 16:18:54 |
| 3days | 200 | 0 | 16:19:00 |
| 7days | 200 | 50,816 | 16:19:04 |
| 30days | 200 | 132,960 | 16:19:07 |

These are **provider-reported feature counts**, not unique flood incidents, people, area or proof of current water. Nonempty products were sampled one feature each; their complete geometry and nationwide scientific coverage were not accepted by this count check. The 7/30-day products exceed the current cap. The [official catalog](https://opendata.gistda.or.th/th/dataset/flood-disaster-data) describes separate retrospective windows; extending the window provides older evidence, not a current flood-state confirmation.

The 29 observed property names include `_createdAt`, `_updatedAt` and `file_name`; this does not establish satellite acquisition time. Their values were not retained or interpreted as observation dates. The accepted normalized feed supplies neither per-feature acquisition time nor valid/clear-observation coverage. API `timeStamp` is response time. A STAC item/scene footprint is not a classified flood mask or proof that every pixel is usable.

## Recommended next implementation

1. **Fix large national collection and operational visibility first.** Measure the current data volume, stream validated pages into staged chunks/indexes with bounded memory and atomic complete-generation promotion, and size explicit storage/time/feature budgets across every contract and reader. Serve geometry through indexed areas or tiles. Keep summaries lightweight. Preserve source-reported counts and a bounded history of empty, failed and oversized runs so the next successful empty query does not hide a recent capacity failure. Retain failure protection; never publish a truncated first 20,000 as a complete country query.
2. **Add a separate historical 7/30-day product view.** Keep the existing 3-day default. Label historical footprints as evidence in that product's retrospective window; use a neutral historical style and show the selected window. Do not infer that a location has remained flooded for 30 days, merge overlapping product counts into incident totals, or assign an acquisition date from retrieval time. Store dated snapshot history independently of the two A/B recovery slots; until acquisition is qualified, its timestamps mean first/last seen in an API query.
3. **Track observations by actual valid coverage and qualified time.** A new image of one region must not refresh the clock for the rest of Thailand or a whole partly imaged province. A missing positive feature does not clear a previous flood footprint unless a later qualified observation covers that location with usable pixels and an explicit negative classification. Where coverage/time is unavailable, display “ยังไม่มีข้อมูลยืนยันใหม่” or “ไม่ทราบความครอบคลุมของภาพ”; do not assert that the satellite has not passed.
4. **Keep current corroborating evidence distinct.** Present HII water/rain, radar estimates and agency warnings with their own source clocks and meanings while satellite evidence is old or unavailable. They can support situation assessment but do not certify a new flood polygon. A future DDPM/local incident feed needs its own source/time/coverage acceptance and explicit reported-incident label.

Suggested area states:

| Evidence | Display meaning |
| --- | --- |
| New qualified positive satellite observation | Detected in the named image/time and valid footprint |
| Historical positive, no later qualified observation | Past detection; current flood state unknown |
| Zero features, coverage unknown | No returned features in this query; current flood state unknown |
| Later usable observation, explicit negative classification | Not detected in that observation; does not certify ground safety |
| Collection failed, partial or over capacity | Refresh unavailable; retain the last complete reference with its original clocks |

The current positive-only Features integration cannot independently distinguish all these scientific states. Its safe default is unknown current state, rather than a fabricated “no flood” or “no satellite pass” status. GISTDA's [remote-sensing explanation](https://demoweb.gistda.or.th/news_view.php?lang=TH&n_id=8062) also describes multiple optical/radar sensors and analysis; cloud cover is not a universal explanation for missing SAR-derived updates.

## Changes and verification

The existing inspector now accepts an explicit, national `compare_windows: true` reviewed request. Normal manual inspection still defaults to one 3-day page. Comparison is bounded to the four fixed windows, rejects district/STAC comparison requests, never publishes, and keeps failures separate from valid zero counts. No new workflow, credential, map default, production flood collection policy, fit or mobile change was introduced.

Targeted diagnostic tests: 38 passed. CI logs for commit `2721906e5e7a3bcec12f33b4f82d4c7b3059842d`: **306 Python tests passed, 29 opt-in HTTP checks skipped; 116 web tests, TypeScript and production build passed**. No live flood-layer reacceptance is claimed from diagnostic-only code changes.
