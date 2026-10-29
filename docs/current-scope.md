# Current project scope

Updated 29 October 2026, Asia/Bangkok. This document records the user's current scope and supersedes earlier local trial plans.

- The product covers Thailand. There is no preferred province, district, pinned local station list or district-only source rollout.
- Fetch a complete country response, then filter province/district views using validated administrative membership. Missing records are unavailable or empty source results, never an all-clear.
- GISTDA publication and its default CLI use the complete retrospective **3days Thailand** product, bounded and stored in chunks. Run `python -m pipelines.gistda.run --publish`; the existing `--three-day` option is an equivalent explicit form.
- The GISTDA inspection Action defaults to 3days and has no district input. It reads one diagnostic page without publishing it. The publication Action collects the complete bounded national query.
- HII targets every available Thailand station from the unfiltered provider response. Current discovery and acceptance are recorded in `thaiwater-national-scope-2026-10-29.json`; the gauge layer is still unavailable until its observation semantics are accepted.
- Daily and hourly weather cover 77 province plus 928 district points. RID and TMD retain their own accepted source coverage; country scope does not fabricate absent observations.

The latest verified running system is described in [the data health release](data-health-area-loading-release-2026-10-29.md) and [the three-day GISTDA release](gistda-three-day-release-2026-10-29.md). Historical evidence and retired instructions are under `archive/` and must not set defaults or define user preferences.
