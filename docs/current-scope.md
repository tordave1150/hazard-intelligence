# Current project scope

Updated 30 October 2026, Asia/Bangkok. This document records the user's current scope and supersedes earlier local trial plans.

- The product covers Thailand. There is no preferred province, district, pinned local station list or district-only source rollout.
- Fetch a complete country response, then filter province/district views using validated administrative membership. Missing records are unavailable or empty source results, never an all-clear.
- GISTDA publication and its default CLI use the complete retrospective **3days Thailand** product, bounded and stored in chunks. Run `python -m pipelines.gistda.run --publish`; the existing `--three-day` option is an equivalent explicit form.
- The GISTDA inspection Action defaults to 3days and has no district input. It reads one diagnostic page without publishing it. The publication Action collects the complete bounded national query.
- HII collects the unfiltered automatic station response nationally every two hours. `python -m pipelines.thaiwater.run --publish` publishes a bounded A/B station envelope. The map and selected-station three-calendar-day history preserve original source wall times, unknown observation UTC/age, separate m/MSL units and neutral markers. The independent national rain_24h product adds observed mm/24h and mm/1h station values with original wall times and unknown UTC window bounds. See `hii-national-release-2026-10-30.md` for acceptance and verification.
- The province comparison covers all 77 provinces in one summary response. The separate 22-basin context uses DDPM boundaries and conservative point matching for HII stations and the 35 connected RID dams; it does not infer upstream/downstream networks or aggregate province products into basin warnings.
- TMD checks twice an hour and collects after one hour; hourly weather checks hourly and collects after four hours or a new Bangkok day. Recent successful products skip provider requests. GitHub scheduling remains best-effort; deadlines and actual source freshness stay visible.
- Daily and hourly weather cover 77 province plus 928 district points. RID and TMD retain their own accepted source coverage; country scope does not fabricate absent observations.

The latest verified running system is described in [the data health release](data-health-area-loading-release-2026-10-29.md) and [the three-day GISTDA release](gistda-three-day-release-2026-10-29.md). Historical evidence and retired instructions are under `archive/` and must not set defaults or define user preferences.

The current province/rain/basin implementation and scheduler recovery are recorded in `province-rain-basin-release-2026-10-30.md`. Routine database verification now covers seven active products.
