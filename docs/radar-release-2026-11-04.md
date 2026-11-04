# Bounded TMD radar image player

4 November 2026, Asia/Bangkok. This C1 increment implements the [qualified TMD composite image product](tmd-radar-acceptance-2026-11-04.md). Numerical QPE and nowcasting remain separate, unaccepted products.

Choose **Map background → Observed radar estimate · TMD**. Play/pause, previous/next, timeline, latest frame and independent opacity operate on at most 13 source images spanning three hours. The selected image's ICT and original UTC time stay visible. Radar and Open-Meteo forecast fills are mutually exclusive; station, dam, warning and flood choices are preserved. The same native image source is used in 2D/3D and basin context without claiming basin rainfall aggregates. Original image colors and TMD's published scale are retained.

New frames stay hidden until successful image-source metadata loading. A failed image is hidden and stops advancement. A stale/unknown feed is hidden and playback is disabled. Latest source observation and retrieval age jointly determine FRESH through 45 minutes, DELAYED through 90, then STALE. Historical frames keep their original times even when the latest feed is fresh. Transparent pixels and missing images never establish zero rain, complete coverage or safe conditions; non-rain echoes remain possible.

## Collection, authorization and storage

`python -m pipelines.radar.run --export apps/web/data/local/radar-capture.json` is an explicitly enabled local preview. Production uses `.github/workflows/radar.yml`, independently of CAP, targeting minutes 7/22/37/52 each hour. Relevant main-branch code pushes also run it. The job waits for its matching production receiver before collecting. Actual scheduling is best-effort; initial release verification does not establish long-term schedule drift.

The Python collector checks the viewer's geometry, unit description and UTC convention, strict manifest grammar, increasing quarter-hour timestamps and source clock agreement. Two image passes must have matching hashes and unchanged source manifest/clock. Limits: 13 frames, 800 KB/frame, 2.8 MB/generation, 180-second collection budget, no provider redirects. PNG CRCs, dimensions, RGBA format and bounded decompression are validated in both the collector and receiver. No provider credentials or numerical raster values are used.

The receiver accepts signed, short-lived GitHub OIDC tokens only for repository ID 1433731657, the named repository/main branch, exact radar workflow and allowed events on GitHub-hosted runners. Other writes are rejected. No new Actions secret is required. The Vercel Blob connection supplies server-side store credentials; no token is exposed to browsers or logged. Blob SDK 2.4.0 avoids the newly introduced vulnerable Zod dependency chain identified by npm audit in the newer SDK; existing unrelated dependency advisories remain outside this increment.

Immutable PNG names bind original observation time to SHA-256. Images are stored in the dedicated public Blob prefix `tmd-radar/`; MongoDB stores only the strict manifest and A/B control pointer. Readers require the pointer's slot/run ID. A serialized publication lock, complete candidate validation, monotonic latest-observation check and atomic pointer promotion protect active metadata. Active and previous generations are retained; older objects are removed after promotion, pending cleanup is visible as a quality issue and excessive pending cleanup stops new uploads. A crashed worker requires explicit lock recovery after it has stopped. Blob CDN caches can outlive origin cleanup.

The connected store is `hazard-radar-live` (`store_k3kJJWvSqH3gymwa`, sin1), linked to the existing hazard-intelligence project. Two earlier empty, unconnected stores created during setup contain no images and are not used by the application. Account quotas still apply: a full 15-minute cadence can create about 3,000 new image objects/month plus initial backfill; this can exceed Hobby's included 2,000 advanced operations. No plan upgrade or paid subscription was requested or activated. Quota failures preserve the last complete generation and become visible in health and frame-age state.

Mongo administration now audits eight active products. `python -m scripts.mongo_admin verify` includes `tmd_radar:composite_rain_rate`; `python -m scripts.mongo_admin rollback --source tmd_radar` can restore the retained metadata generation. Lock recovery uses the existing exact-token `unlock` flow after confirming the writer stopped. Cleanup applies only to this product's dedicated object paths and collections.

## Verification

Local checks: 285 Python tests, 100 web tests, 29 HTTP checks, TypeScript and production build. Browser review used actual captured TMD images and confirmed loaded-frame timestamps, playback, original gaps, opacity, radar/forecast exclusivity, retained 35 dam markers, 2D/3D and 390-pixel mobile layout with no horizontal page overflow. A corrupted local image was rejected and hidden; the file was restored. A temporary QA clock two hours ahead verified STALE/disabled playback without modifying original source timestamps; that QA route was removed.

Three independent Mercator control calculations from the provider corners cover Bangkok, Chiang Mai and Hat Yai. This verifies application placement math, not independent radar geodetic calibration or pixel coverage. No rain amount is inferred from those control points.

Production deployment, first publication, delivered-object hashes, database retention and runtime observations are recorded in the production receipt after verification. The first real pipeline and elapsed-time evidence must be distinguished from a claimed precise 15-minute schedule.
