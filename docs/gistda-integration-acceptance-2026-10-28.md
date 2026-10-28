# GISTDA integration scope and acceptance — 28 October 2026

This is the current interpretation of the supplied `GISTDA_Data_Dictionary_Integration_Notes.md`, reconciled with the [national release evidence](gistda-national-query-release-2026-10-28.md). The original Downloads file is unchanged. Its statement that Disaster Platform is not connected is historical: the bounded national reader/collector is connected. Connected engineering does not establish complete satellite coverage, scientific accuracy or unrestricted redistribution rights.

## Product and time

The user clarified on 28 October that GISTDA `1day` means **ย้อนหลัง 1 วัน / the previous one-day window**. A query on 28 October may retrieve the 27 October product. It is retrospective, not a forecast or an assertion of today's flooding.

This product definition does not supply a machine-verifiable date for each returned feature. Do not calculate `observed_at` or a product date as `fetched_at - 1 day`: publication delays, repeated queries and unknown cutoffs make that unsafe. Keep the existing `product_window=1day`, null `observed_at`, `observation_time_status=NOT_SUPPLIED`, and independent UTC response/retrieval/ingestion instants. UI displays Thai time and the retrospective label. Query freshness describes the query, not satellite observation age. Changing the weather forecast date does not change GISTDA's window.

## Evidence and release decisions

| Use case | Required evidence / present scope |
|---|---|
| Bounded reference map | Checked geometry and coordinates, canonical administrative identities, explicit product/window and timestamps, complete bounded query, failure retention and source attribution. Current integration supports this qualified scope. Resource-specific reuse terms remain unresolved, not silently marked approved. |
| Current dated flood situation | Verified product/observation interval, publication latency, satellite coverage and representative nonempty 1day validation. Retrieval success alone is insufficient. |
| Area/exposure metrics | Provider definitions and units, appropriate area calculation, overlap/deduplication and relevant methodology. These fields remain excluded. |
| Risk, depth, ETA or alerts | Separately accepted data and validated decision methods. Flood footprints alone do not establish these quantities. |

Unknown units for excluded fields do not stop geometry development. Inspect the actual products used by the release; other windows, flood recurrence and water hyacinth are separate optional scopes. An official provider schema or authorized samples can support an adapter, with validation and explicit unknowns; a sample is not a stable provider contract.

The separate ArcGIS layers have their own seven-field schemas, service/extent reference 3857, source reference 32647 and geometry metadata units `esriMeters`. None sets defaults for Disaster Features business units, coordinate reference or record limits. STAC asset footprints and nominal item datetimes do not automatically become flood masks or per-feature acquisition times. See [dictionary reconciliation](gistda-dictionary-reconciliation-2026-10-27.md).

## Retention and source terms

Production retains only the validated geometry, generated feature IDs, canonical administrative references, fixed source/query metadata and timestamps. Raw provider properties, IDs, creator fields, links/assets and credentials are discarded. No new raw-response archive is enabled. The national collection keeps at most two complete 4-MiB envelopes; the retained pilot has its separate two-envelope 2-MiB policy.

Use value-free diagnostic receipts, source-file hashes and adapter versions for routine audit. A separately needed raw sample requires explicit scope, secret removal, restricted storage and a defined deletion deadline before exporting it; it must not enter the public repository/API or browser. This replaces the supplied note's blanket raw-payload retention recommendation.

The [official catalog](https://opendata.gistda.or.th/dataset/flood-disaster-data) and the [specific 1day resource](https://opendata.gistda.or.th/th/dataset/flood-disaster-data/resource/062a08da-a6a9-4db7-9af7-1d345e38563a) were previously reviewed with `License not specified`. Keep display, caching, download/redistribution and commercial use separate when reviewing applicable account/product terms. Catalog omissions do not settle permission in either direction. The [technical manual](https://disaster.gistda.or.th/manual_api.pdf) supports technical integration, not a blanket bulk-data license. Agency contact is an optional route to resolve a specific gap; no message is sent or new permission inferred by this change.

## Capacity and failure behavior

The existing national path permits 100 results/page, 10 requests, 1,000 features, 100,000 coordinate positions, 4 MiB cumulative response data and 120 seconds. Per-feature geometry bounds also apply. These are application budgets, not provider maxima.

Oversized, timed-out, incomplete, repeated or changing-count queries do not promote a partial snapshot. Retain the last complete A/B generation, record failure and downgrade query freshness. The map panel distinguishes capacity/time/completeness failures using fixed messages, shows prior response/retrieval timestamps and uses gray reference footprints. Never echo arbitrary provider errors. If there is no snapshot, show unavailable rather than an empty successful observation.

Do not raise limits blindly when a flood event exceeds them. A larger product needs a separately validated tile/static or spatially partitioned path, preserving product/date/scope and safe credential handling. Count/duplicate checks without a provider version token do not prove an atomic upstream snapshot.

Current operation: `python -m pipelines.gistda.run --publish --national`; `gistda.yml` targets 09:27 ICT daily. The reviewed push operation is `publish_thailand_1day`. Rollback source `gistda` addresses national slots; `gistda_pilot` addresses preserved pilot slots. These are runbook commands, not actions executed by this document review.

## Remaining evidence

1. Inspect an authorized real nonempty **1day** response and a representative set of dates/locations. A nonempty 30days sample is separately labelled and cannot close this item.
2. Compare a dated product against suitable independent/event evidence, reporting spatial disagreement, missed observations, coverage and latency rather than inferring accuracy from valid polygons.
3. Exercise full supported capacity and failed-refresh retention locally; distinguish synthetic capacity checks from real peak-event/browser/device performance.
4. Review applicable resource/account terms for the exact display/cache scope and record the evidence. Define any future area/exposure metrics separately.

The current live evidence records a complete empty national query, not a real nonempty 1day validation. Synthetic tests cannot close the scientific/data-availability gaps above.

## Verification of this change

58 targeted Python tests passed, including a complete 1,000-feature/10-page synthetic query and a rejected 1,001-match refresh that preserves the prior national generation and records its fixed capacity failure. 21 frontend tests passed, including safe failure messages that never echo unknown error text. TypeScript and the production build passed.

Local browser verification used an explicitly synthetic nonempty national snapshot with a capacity-failed refresh. The API retained one prior footprint, `observed_at=null`, `product_window=1day` and DELAYED query freshness. The panel showed the retrospective Thai/English label, prior timestamps and capacity reason in 2D/3D; methodology showed the 28/27 October example. Browser warnings/errors were empty. The temporary QA snapshot and owned server/tab were removed/stopped; no credential, source fetch, Atlas write, deployment or agency message was involved. Screenshot: ignored `artifacts/gistda-retrospective-review-2026-10-28.jpg`.
