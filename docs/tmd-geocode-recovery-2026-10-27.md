# TMD CAP geocode recovery — 2026-10-27

## Actual failure and retained data

Scheduled TMD runs 40428424750 and 40463193626 failed during collection. The latter's sanitized diagnostic was `stage=collect`, `error_type=ValidationError`. Database audit had succeeded; publication/verification did not run. The last complete published feed remained active.

The official live feed was fetched read-only. Document `TMD20261027054131_2` contains 31 geocodes, including `R-07` under `valueName=ISO3166-2`, alongside 30 recognized Thai province codes and 123 original polygon rings. The old transform sliced every such code as though it were TH-nn, producing the invalid canonical ID TH-P-7 and rejecting the whole feed. No interpretation of R-07 as a province or region is justified.

The [CAP 1.2 specification](https://docs.oasis-open.org/emergency/cap/v1.2/CAP-v1.2-os.html) defines geocode namespaces/values and permits multiple geographic descriptions. Unrecognized source codes are preserved as agency evidence; they must not be promoted into guessed canonical geography.

## Narrow repair and release order

- Only exact TH-nn values that map to the project's verified province registry enter area_ids. Python and TypeScript enforce the same strict canonical set. Original source_areas, unknown code, wording, classifications, validity times and polygons remain unchanged.
- The warning API discloses unmapped codes across the full latest feed in geography_issues. It explicitly does not assign unresolved codes to the requested area. The panel discloses incomplete province matching and shows original unresolved codes when a message is selected.
- Existing stored schema-2.0 feeds remain readable; no database migration or history rewrite is needed. Whole-feed validation, last-good retention and A/B size/count bounds remain mandatory.
- Deploy the compatible reader first. Only after deployment succeeds, publish a fresh complete provider feed with the corrected collector. A main-only, path-filtered publication-request trigger uses the existing TMD job, secrets and concurrency group; there is no new token, broader database scope or website-triggered ingestion.
- Provider failures now report a bounded public document ID and fixed reason. JSON Schema failures report the trusted schema path and validator, never raw values, connection strings or exception text.

## Local verification

The exact real CAP regression retained all 31 original geocodes and 123 polygon rings, mapped only 30 known provinces and rejected a forged TH-P-07 reference. Unknown R-07, TH-99 and TH-1 test cases remain verbatim without guessed geography. Frontend validation/disclosure tests also reject invented canonical IDs.

The full offline suite passed **119 Python tests** (18 running-server tests skipped). **15 frontend tests**, TypeScript and production build passed. Before the repair, all **18 production HTTP checks** passed; the checks now additionally assert truthful geography-issue disclosure and must run again after deployment.

The first full corrected fetch encountered a bounded transport failure and did not publish. A subsequent diagnostic collection, with safe per-document identification, fetched and validated all **12/12** live messages. Its serialized feed was **1,553,942 bytes**, below the **2,097,152-byte** envelope bound. Isolated A/B publication/read-back passed. This is an actual complete provider collection, not a synthetic production feed. Production publication and browser verification are still pending the ordered release.

Evidence is retained under ignored artifacts/phase6-tmd-2026-10-27. The attributed real CAP fixture and its checksum are added with the collector repair. Source license/attribution follows the already accepted public TMD CAP channel; this repair does not broaden acceptance to registered forecast/radar products.

## Verified production outcome

Compatible reader c573cb6 deployed and was verified publicly before writer 1260831 was pushed with reviewed publication request 2026-10-27-01. Run [40501283729](https://github.com/tordave1150/hazard-intelligence/actions/runs/40501283729), job 122179305342, completed every step: request validation, audit, complete fetch/publication, read-only verification and post-publication audit. It published **12/12** real messages at **27 October 2026 19:08:12 ICT**. The API then reported FRESH/SUCCESS, completeness 1.0 and null error_summary, with the exact source R-07 disclosure and all 30 canonical provinces/31 raw geocodes/123 polygon rings still present.

The post-release HTTP suite passed **18/18** checks. CI passed **120 offline Python tests**, **15 frontend tests**, TypeScript and build. At the capture, actual source types were 6 Alert, 5 Update and 1 Cancel; derived states were 1 current, 6 expired, 2 cancelled and 3 superseded. Browser checks confirmed current-time validity independent of the forecast date, explicit source-code limitations and gray previous-message outlines. The earlier transient collection error did not persist into the successful publication.

The minimum compatible frontend rollback target is c573cb6. The new isolated regression covers old feed → feed with unknown code → rollback → re-publication; production was not rolled back for testing. Full release evidence and remaining platform/device gates are in [the Phase 6 verification report](phase6-release-verification-2026-10-27.md).
