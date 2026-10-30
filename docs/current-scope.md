# Current project scope

Updated 30 October 2026, Asia/Bangkok. This document records the user's current scope and supersedes earlier local trial plans.

- The product covers Thailand. There is no preferred province, district, pinned local station list or district-only source rollout.
- Fetch a complete country response, then filter province/district views using validated administrative membership. Missing records are unavailable or empty source results, never an all-clear.
- GISTDA publication and its default CLI use the complete retrospective **3days Thailand** product, bounded and stored in chunks. Run `python -m pipelines.gistda.run --publish`; the existing `--three-day` option is an equivalent explicit form.
- The GISTDA inspection Action defaults to 3days and has no district input. It reads one diagnostic page without publishing it. The publication Action collects the complete bounded national query.
- HII collects the unfiltered automatic station response nationally every two hours. `python -m pipelines.thaiwater.run --publish` publishes a bounded A/B station envelope. The map and selected-station three-calendar-day history preserve original source wall times, unknown observation UTC/age, separate m/MSL units and neutral markers. Rain gauges remain unconnected. See `hii-national-release-2026-10-30.md` for acceptance and verification.
- Daily and hourly weather cover 77 province plus 928 district points. RID and TMD retain their own accepted source coverage; country scope does not fabricate absent observations.

The latest verified running system is described in [the data health release](data-health-area-loading-release-2026-10-29.md) and [the three-day GISTDA release](gistda-three-day-release-2026-10-29.md). Historical evidence and retired instructions are under `archive/` and must not set defaults or define user preferences.
