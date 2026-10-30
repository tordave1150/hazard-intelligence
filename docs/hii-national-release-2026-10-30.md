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

Local validation: 251 Python tests passed, 22 opt-in HTTP tests skipped; 57 web tests passed; TypeScript and production build passed. The HII local HTTP flow returned 802 station rows and a real 432-point history with observation freshness UNKNOWN.

Production publication [41077296955](https://github.com/tordave1150/hazard-intelligence/actions/runs/41077296955) succeeded at 22:04 ICT on 30 October. It returned 808 automatic rows: **805 Thai stations in 76 provinces**, three excluded foreign rows and 35 separate manual rows. All 805 observation UTC timestamps remain null; query freshness is FRESH, observation freshness UNKNOWN, and the source has zero row-format quality issues. All six active database products passed the read-only generation/index/retention verifier. The first HII generation occupies one of a maximum two documents.

All **22 production HTTP checks passed**. Additional real checks confirmed Chiang Mai 48 stations, Nakhon Ratchasima 20, Songkhla 19, and an empty source result for Amnat Charoen. An ordinary district filter returned four stations. The province summary includes the same HII product. These are snapshot counts, not a claim of area-wide water conditions or permanent inventories.

The published sample station history returned 421 timestamped rows with 415 values over 28–30 October (reported calendar dates), with MSL units and unknown observation timezone intact. The production Data health page showed HII SUCCESS/OK, a two-hour cadence, 805 station reports and 805 separately disclosed unknown observation ages. See the [count-only production receipt](hii-production-receipt-2026-10-30.json).

Production browser verification covers national clusters, station details/history, ordinary area selection, 2D/3D and a 390px mobile panel. The province view showed 48 stations; a second selected station displayed 416 valid history values. Native point selection changed the station correctly in 3D, and a cluster click within a TMD polygon preserved the HII panel. The final browser console had no errors. The review fixed style-load initialization and ensured native HII points/clusters take click priority over overlapping weather, warning and satellite polygons. Proof images are local ignored artifacts under `artifacts/hii-*-production-2026-10-30.png`.
