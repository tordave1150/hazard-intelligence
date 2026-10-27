# Phase 6 release verification — 2026-10-27

Story: selecting a region/province/district reads bounded Atlas snapshots through the public APIs, then renders source-specific forecast/report/validity times, units, provenance and honest unavailable states on one 2D/3D map. No browser action starts provider ingestion.

Production: https://hazard-intelligence-lime.vercel.app/ . Functional fixes: c573cb6 (CAP reader), 1260831 (complete CAP collector/publication), 6356ebe (dialog focus). GISTDA product questions remain deferred at the user's request; no new GISTDA data ingestion or agency communication occurred.

## Results and repairs

| Boundary/check | Result | Evidence |
|---|---|---|
| Production HTTP contracts | PASS | 18 tests before repair and 18 after recovery; dates/units, canonical IDs, rejected queries, unavailable sources, no write route and geography disclosure |
| Offline Python suite | PASS | 120 tests in CI; running-server HTTP suite is opt-in and tested separately against production |
| Frontend semantics | PASS | 15 Vitest tests; TypeScript and production build passed |
| Desktop navigation/rendering | PASS | 1440x1000: Thailand → Northern → Chiang Rai → Mae Sai; 2D/3D terrain, probability legend, metric extrusion and return navigation |
| Mobile responsive flow | PASS | 390x844: layer/area drawers, same hierarchy and Thai search Ongkharak → TH-D-2604; DOM client/scroll widths both 375px |
| Source-time independence | PASS | Forecast switched to 28 October while RID retained 27 October and CAP validity used actual current time |
| RID semantics | PASS | Real Nong Pla Lai 109.76% of normal capacity displayed without clamping; 179.74 million m³, date-only observation time and no downstream-hazard inference |
| CAP source quality | REPAIRED | Real source R-07 preserved, only 30 known provinces mapped, all 31 geocodes/123 polygon rings retained; API/panel disclose unresolved scope |
| CAP production recovery | PASS | Run 40501283729 on 1260831 published all 12/12 messages, then verified all products/indexes/retention and audited storage |
| CAP actual message states | PASS at capture | 1 CURRENT, 6 EXPIRED, 2 CANCELLED, 3 SUPERSEDED; source types 6 Alert / 5 Update / 1 Cancel. These counts change with time/provider updates |
| Source-dialog keyboard access | REPAIRED | The old effect captured the auto-focused close button. Capturing the opener before mounting now restores focus after Escape/close from both header and area-panel entry points; Tab wrap and aria-modal verified |
| Browser console | PASS | No warning/error entries observed during the connected-browser scenarios |

The saved Playwright specification now includes focus restoration. It was **not executed by an external Playwright runner**; the documented actions/assertions were exercised through the approved connected-browser tools. Responsive viewport checks are not physical-phone or GPU-memory benchmarks.

## Independent ingestion and bounded storage

Scheduled weather run **40457108471** succeeded on 27 October (12:45:17–12:56:28 ICT). Scheduled RID run **40460338455** succeeded (13:18:41–13:19:32 ICT). TMD scheduled runs 40428424750/40463193626 failed on the provider's noncanonical geocode; the last complete feed remained available with FAILED health and stale/paused presentation. The corrected, reviewed publication succeeded at **19:08:12 ICT** in run 40501283729, cleared error_summary and restored FRESH/SUCCESS. Its reader had been deployed first, so the new raw code was readable before publication.

The post-publication read-only verifier reported:

| Product | Active records | Stored documents | Bound | Unique index |
|---|---:|---:|---:|---|
| Weather | 1,005 | 2,010 | 2,010 | Verified |
| RID | 35 | 70 | 70 | Verified |
| CAP envelope | 1 (12 messages) | 2 | 2 | Verified |

There were zero writer-lock documents after publication. The full locally collected 12-message envelope was 1,553,942 serialized bytes, below its 2,097,152-byte limit. Source collections were not cleaned up or expanded beyond A/B retention. Original XML/wording, original CAP references, issue/effective/expiry times and polygons remain preserved.

The observed daily jobs started later than their cron targets. Source cadence labels now explicitly allow execution delay; retrieval/source timestamps determine freshness. [GitHub documents scheduled-run delays and possible dropped queued runs under load](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule). No exact-time or real-time service guarantee is asserted.

## Recovery qualification and remaining gates

The saved **26 October isolated real MongoDB 8.0.34** report passed publication/empty feed, CLI rollback for all three sources, interrupted candidates, orphan-lock recovery, real database outage without local fallback and database restart/index recovery. That real-engine run was not repeated. A new 27 October regression additionally passed legacy CAP feed → unmapped-code feed → rollback → re-publication in isolation. Production publication/read-back/index/retention verification then passed on real Atlas.

For any frontend rollback with the newly published CAP feed, **c573cb6 is the earliest compatible target**. Older readers reject R-07, even with valid canonical area_ids. Use a compatible deployment; an older-reader recovery requires a separately planned, intact prior data generation and maintenance decision. No production rollback, unlock or outage was initiated merely for testing.

The Vercel connector was rechecked with the intended team team_V0dZUHXqiEyo9Tu4vJN3gCoO: get_project(hazard-intelligence) still returned 404 and project search returned no match. GitHub Vercel statuses and the public site verify deployments, but platform configuration, isolated deployed rollback and Atlas infrastructure failover remain unverified without the appropriate project access/environment. Physical-device/GPU benchmarking also remains unperformed. GISTDA/HII/basin/registry-currency gates remain as recorded separately. These limitations keep the all-work-complete shutdown condition unsatisfied.

## Saved evidence

Ignored local artifacts retain production HTTP JUnit reports, sanitized source/retention receipts and screenshots:

- artifacts/phase6-production-http-2026-10-27.xml
- artifacts/phase6-production-http-after-recovery-2026-10-27.xml
- artifacts/phase6-tmd-2026-10-27/production-verification.json
- artifacts/phase6-retention-audit-2026-10-27.json
- artifacts/phase6-browser-regression-2026-10-27.json
- artifacts/phase6-desktop-maesai-3d.png
- artifacts/phase6-tmd-unmapped-code-disclosure.png
- artifacts/phase6-mobile-maesai.png

The public CAP regression fixture and checksum are tracked under tests/fixtures/tmd. See [the incident and recovery record](tmd-geocode-recovery-2026-10-27.md) for the precise scope of the repair.
