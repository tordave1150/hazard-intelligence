# HII national station observations and selected-station history

Scope: Thailand, with ordinary region/province/district filters and no station allowlist. Implemented 30 October 2026, Asia/Bangkok.

## Data acceptance

- Fixed official public `waterlevel_load` endpoint, no embedded portal keys, redirects or user-provided URLs. Each refresh reads the complete unfiltered automatic response with byte/time/retry budgets.
- Station identity is the provider station ID, not the observation row ID. Canonical Thai provinces and districts determine filters. Other province codes are preserved in excluded-record accounting. Manual rows remain separate and discharge is never substituted for a water level.
- `waterlevel_msl` means meters above mean sea level, per the official ThaiWater manual. The separate meter field is retained independently. These are source-reported station values, not flood depth, area averages, calibrated measurements or cross-station risk scores.
- Provider wall times omit timezone. Original strings remain visible, `observed_at` stays null, and observation age remains UNKNOWN. Retrieval freshness can be FRESH independently. Markers are neutral and do not reuse undocumented provider warning thresholds.
- One validated envelope per A/B slot, maximum two retained generations. Invalid/incomplete candidates preserve the current generation. Current verifier covers six active products; retired products require an explicit audit option.
- Public portal access is verified. Numeric quotas, service guarantees and unrestricted live-product licensing are not asserted. Attribution identifies HII / ThaiWater and original measuring agencies for this personal non-commercial project.

## History and operation

Selecting a published Thai station calls the fixed public `waterlevel_graph` endpoint with its station ID and last three **reported calendar dates**. No arbitrary date, host or unknown station input is accepted. Null gaps, source timestamps and meter/MSL units remain intact. A bounded 64-entry, 15-minute cache and eight concurrent request limit avoid collecting history for the entire inventory. Graph data can be newer than the collected map snapshot. No forecast or timezone conversion is inferred.

`Latest HII Thailand river level stations` runs every two hours at minute 43 UTC (01:43/03:43/…/23:43 ICT targets; execution can be delayed). It reuses existing MongoDB repository secrets and needs no HII credential. Manual run: `python -m pipelines.thaiwater.run --publish`. Rollback: `python -m scripts.mongo_admin rollback --source thaiwater`.

## Verification

Initial real source review: 805 automatic IDs, 802 canonical Thai rows across 76 provinces, three provider-labelled foreign rows, 35 separate manual rows. These counts describe a response and are not a permanent inventory requirement. All 77 provinces remain navigable. The sampled graph request returned 432 timestamped rows with 420 values; null points are retained.

Local validation: 251 Python tests passed, 22 opt-in HTTP tests skipped; 57 web tests passed; TypeScript and production build passed. The HII local HTTP flow returned 802 station rows and a real 432-point history with observation freshness UNKNOWN. The full local smoke run had 19 passes and three GISTDA failures because its ignored local snapshot was absent; production smoke verification is required after deployment.

Production publication and browser evidence will be recorded here after the first deployment and real ingestion cycle.
