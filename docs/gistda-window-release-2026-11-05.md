# Complete GISTDA products and bounded historical display

5 November 2026, Asia/Bangkok. This increment addresses the [20,000-feature failure](gistda-availability-2026-11-04.md). Production collection results are recorded separately after the compatible reader is deployed and the real run completes. Map fit, viewport and mobile/CSS adjustments remain deferred.

## Product and observation meaning

The default remains the national **3days** product. Independent **7days/30days** selectors are historical references. They never substitute for an empty 3-day query automatically. Query response, retrieval and ingestion clocks remain separate from unknown satellite acquisition time and valid/clear image coverage. An empty successful query does not establish no flood, a missed satellite pass or a receded flood. New imagery elsewhere cannot refresh an unobserved location. Historical windows and archived queries use neutral reference styling.

Provider feature counts are fragments/records, not unique incidents or affected area. Different provider identities can refer to identical geometry in retrospective products; retain those distinct records. Hash provider identity/geometry/admin membership for storage identity, without exposing provider IDs, raw properties or links. Duplicate source identities within a paged collection still reject publication. No area/depth/impact metric, acquisition date, geometry repair, reprojection or inferred negative observation is introduced.

## Collection and storage

`python -m pipelines.gistda.run --publish` collects the default 3-day product through the new streaming path. `--three-day` is equivalent; `--all-windows` independently collects 3/7/30 days. The existing daily Action uses all windows and waits for the compatible production reader. No new workflow, secret, paid plan, object store or external account is added. Existing legacy collections remain intact and readable until their control pointer changes.

Source pages use fixed HTTPS routes and API-Key headers; redirects and returned URLs are not followed. A bounded 1,000-row source-page measurement confirmed the provider supports that limit. The sampled 7/30-day pages were approximately 2.6/3.2 MB, with normalized 100-row gzip blocks totaling approximately 0.60/0.62 MB per 1,000 sampled rows. This is a sizing sample, not a complete product acceptance or guaranteed compression ratio.

The collector keeps one bounded source page in memory and spools normalized rows into SQLite on the runner. It checks source counts throughout pagination, unique hashed source identities, canonical province/district relationships, geometry syntax/topology and Thailand coordinate bounds. After complete collection it writes sorted district-specific chunks, at most 100 features / 1 MiB uncompressed each. Each immutable gzip object binds to SHA-256 of the original normalized bytes. Metadata includes exact area counts and chunk membership; no full country feed is assembled in memory or sent as one Mongo document.

Explicit budgets per product: 250,000 features, 250 source pages, 768 MiB received source bytes, 512 MiB normalized bytes, 12 million positions, 1,200 source-collection seconds, 5,000 stored chunks and 128 MiB compressed objects. A run shares 300 provider requests and a 45-minute collection deadline across the windows; the Action has a 60-minute job timeout. Exceeding a budget or encountering incomplete/changed/invalid source data retains each last complete product and records the failure.

New collections are `gistda_flood_objects`, `gistda_flood_manifests` and bounded `gistda_flood_runs`. A single nonexpiring exact-token publication lock serializes promotion/garbage collection. Complete object writes and manifest accounting precede the atomic per-window control pointer. Current and previous generations are protected, including original legacy storage during migration; rollback validates retained objects before pointer changes. Ordinary Mongo audits check compressed object metadata; `python -m scripts.mongo_admin verify --deep-flood` additionally downloads and validates active gzip bytes. Audits do not create indexes.

The application reserves at most **320 MiB of compressed flood objects** and checks projected whole-database data/index bytes against a conservative **400 MiB operational ceiling**. These are application guards, not discovered provider billing/plan limits. There is no paid upgrade. If current/previous protected products cannot fit, the candidate is rejected. Existing Blob/Radar upload reservations are unaffected.

## Query history and retention

Keep one completed 3-day query snapshot per UTC day, targeting 30 days, plus protected current/previous generations. This archive records when a query was retrieved, not when a satellite observed a location. The separate 7/30-day products retain their own current/previous complete queries; they are not a claim of thirty daily observations.

Under the compressed storage budget, older unprotected archive geometry can be evicted while its query metadata/counts remain available within the history period. The API/UI explicitly mark such entries as summary-only and never draw another snapshot's geometry in their place. Available history starts with actual retained queries; missing past snapshots are not backfilled with invented dates. Legacy source snapshots outside the new managed cache are preserved.

Failure history survives later successful empty queries: status includes last failure, last nonempty query when known, consecutive empty queries and provider-reported count when available. The last 100 run records are retained separately. No historical acquisition timestamp is inferred from filenames or `_createdAt`/`_updatedAt`.

## API and browser

`/api/flood-products` defaults to `window=3days`; `window=7days` and `window=30days` are explicit independent selections. `generation` pins a retained query and all subsequent pages. Unknown windows, duplicate parameters, invalid cursors and cross-window generations are rejected. Metadata responses use `no-store` for readiness/health; manifest/catalog caches remain bounded. Every delivered object is size-, decompression-, SHA-256-, schema- and administrative-membership checked before returning geometry.

Large country/region/province results show indexed counts and child-area navigation. Small selected areas load their complete geometry with at most four requests concurrently and a 2,000-feature browser bound. Large districts load a clearly labelled 100-feature page, with previous/next controls and the full area count. The legend states how many shapes are actually displayed; a page is never labelled a complete national result. No province flood fill is fabricated from counts. Source overlays/background selection remain independent.

## Local verification

Local validation covers more than 20,000 input records, corrupt/compressed-bomb data, identity/count changes, failed writes, storage exhaustion, pointer preservation/rollback, archive geometry eviction with retained metadata, source error versus valid zero, historical clocks, country summaries, complete small-area loading, explicit large-district pages and mixed-generation rejection.

Initial full checks: 320 Python tests (29 opt-in HTTP checks skipped), 123 web tests, TypeScript and production build passed. Three additional operational regressions subsequently passed in the 16-test streaming suite. All 29 local HTTP checks passed. Desktop browser QA used explicit synthetic local data and verified empty-state failure history, 3/7/30 selection, country → province → district navigation, 100-of-3,001 paging, the next page and selection of an earlier query with its original retrieval clock. Browser console errors were absent. Synthetic QA is not source acceptance, and fit/mobile were not changed or tested in this increment.

Follow-up tests additionally cover cross-window isolation through the manifest cache, independent per-window failure, bounded receiver readiness and failure breaking a consecutive-empty streak. Metadata audits use a batched object-header query; deep audits stream compressed objects in bounded cursor batches rather than issuing a database round trip for every chunk. Independent catalog/history/run reads are parallelized.
