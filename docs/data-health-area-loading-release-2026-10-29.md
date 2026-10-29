# Data health and area loading — 29 October 2026

Production: [Hazard Intelligence](https://hazard-intelligence-lime.vercel.app/) · [Data health](https://hazard-intelligence-lime.vercel.app/health).

## Accepted changes and observed results

TMD's public message `TMD20261028172215_2` supplies an effective time of 28 October 18:00 ICT but an expiry of 28 October 06:00 ICT. Previously this stopped publication of the entire feed. Normalization now preserves both original instants, adds `INVALID_PROVIDER_INTERVAL` and treats validity as `TIME_UNKNOWN`. It never guesses a replacement expiry or renders this message as a current warning. Unflagged or incorrectly flagged inverted intervals still fail validation. Missing times remain unknown; legacy valid records remain readable.

[TMD run 40903695037](https://github.com/tordave1150/hazard-intelligence/actions/runs/40903695037) completed publication, retention verification and storage audit. Production readback returned 8 of 8 messages, `SUCCESS`, `FRESH`, completeness 1, and one explicit provider time-quality issue. This issue remains visible on the map and Data health page.

The health page independently displays collection result, attempt/success times, data freshness, source quality, workflow links and schedule evidence. A planned HII source is not a failed active integration. GISTDA uses query freshness for collection health while retaining unknown satellite acquisition age. Overdue deadlines follow the actual UTC cron slots, with explicit grace periods; late manual runs do not shift the scheduled clock. TMD/hourly runs persist `RUNNING` before collection and preserve the prior successful generation on failure.

GISTDA now serves a geometry-free summary first. The server builds a bounded, generation-specific administrative membership index from IDs/codes without transferring national geometry to the browser. Enabling the layer requests only pages containing the selected area. The client still requires consistent generation, metadata, IDs and the complete selected-area count before publishing shapes to the map. Summary counts cannot be mistaken for empty geometry results. The previous paginated API remains available.

Production measurements for generation `c49fe6c4-def7-4162-9684-45d0d043c83a`:

| View | Count | Browser response size | Geometry pages |
| --- | ---: | ---: | ---: |
| Thailand summary | 7,846 | 1,657 bytes | 0 |
| Nakhon Nayok summary | 113 | 1,666 bytes | 0 |
| Nakhon Nayok detail | 113 unique IDs | 174,769 bytes total | 5 |
| Ongkharak summary | 0 | 1,668 bytes | 0 |
| Ongkharak completed detail | 0 | 1,666 bytes | 1 empty response |

The prior initial national geometry transfer was 15,919,675 bytes over 79 pages. These sizes measure GISTDA payloads, not the entire website. Opening Thailand with the layer enabled explicitly loads national geometry. Administrative membership is not polygon clipping or proof of satellite coverage. Empty results still do not establish no flooding.

## Hourly resilience

The failed production attempts were made observable as `transport_error` / `ReadTimeout`, while credential-free HTTPS host checks returned HTTP responses. Provider queries for the same point batches succeeded from the local environment. Hourly collection now shares one requests Session for connection reuse and reduces a slow 25-point batch to 5-point batches, without skipping previously uncollected locations. All attempts still consume the shared rolling provider budget; HTTP authorization/quota errors are not routed to another service. Only a validated complete 1,005-point generation may replace the current product.

[Recovery run 40906953860](https://github.com/tordave1150/hazard-intelligence/actions/runs/40906953860) completed successfully after connection reuse was added. It published all 1,005 hourly point forecasts for 29 October and passed database pointer/retention verification. The successful run did not need the smaller-batch fallback. Production status readback confirms `SUCCESS`, `FRESH`, monitoring `OK`, no error summary, and last success `2026-10-29T16:02:15.468849Z` (23:02 ICT). This establishes successful recovery, without asserting that every earlier timeout had the same root cause or that the upstream can never time out again.

## Verification

- Python: 255 passed; 21 HTTP integration checks skipped in the offline suite.
- Web: 51 tests passed, TypeScript and production build passed.
- Local running-app HTTP suite: 21 passed, including synthetic multi-page, nonempty scoped and completed empty-area queries.
- Production targeted HTTP suite: 7 passed, including health, scoped summary/detail agreement and unsupported-query rejection.
- Browser: national count 7,846 with the layer off; Nakhon Nayok displayed all 113 footprints after enabling the layer. Data health checked at desktop and 390-pixel mobile viewport with no horizontal overflow; night-theme contrast checked. Local synthetic preview files and server were removed after QA.

ThaiWater discovery and remaining acceptance facts are in [the separate review](thaiwater-access-review-2026-10-29.md). No unverified gauge product was published.
