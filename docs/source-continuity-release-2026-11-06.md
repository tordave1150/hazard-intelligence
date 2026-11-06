# CAP geometry recovery and bounded adaptive GISTDA pagination

6 November 2026, Asia/Bangkok. This implements the approved next items 1–2. Map fit/mobile work and further nowcasting/QPE acceptance remain deferred.

## TMD CAP root cause and accepted recovery

The failed public CAP run was reproduced read-only. `TMD20261105175255_2` has 73 source polygon strings; polygon index 2 contains a trailing-comma coordinate token (`13.466097,100.985718,`), and its first/last pairs differ. The previous parser ignored extra comma components, then the polygon closure/topology check rejected the whole feed. The [original public document](https://www.tmd.go.th/uploads/CAP/CAPTMD20261105175255_2.xml) is preserved byte-for-byte as a test fixture (SHA-256 `c5c0f264699d26109a8de94e3a5a053c2d8d497c0998a8dbd7f6e395a2ed16ac`). The [OASIS CAP 1.2 polygon definition](https://docs.oasis-open.org/emergency/cap/v1.2/CAP-v1.2-os.html) requires at least four coordinate pairs and equal first/last pairs.

The new qualification is explicit:

- Message identity, Actual/Public status, sender, references, clocks, text and canonical province membership still pass the existing checks.
- Each source polygon must have exactly two finite coordinates per token, accepted coordinate bounds, a closed ring and valid positive-area topology. Existing per-ring/message/document/envelope bounds remain in force.
- If a polygon is malformed, the message is retained with `geometry_quality: INVALID_PROVIDER_GEOMETRY`, `geometry: null`, all original `source_polygons` strings and controlled `geometry_issues` indices/reasons. The **entire message outline** is suppressed; no ring is repaired and no valid subset is drawn as a complete warning area.
- Valid original polygons remain unchanged. `VALID` and `NOT_SUPPLIED` distinguish a valid outline from an absent one; older valid records without this optional qualification remain readable.
- The message text, original dates and explicit province references remain available with a visible geometry-quality note. Geometry qualification does not extend expiry, assign an unmapped code, create a district warning or certify current conditions.

All listed feed items must still be fetched and processed. Transport, unsafe XML, schema/identity/time/reference errors and oversize geometry still stop publication and preserve the previous complete feed. Invalid polygon metadata is not counted as a missing or ignored warning. Safe diagnostics now include a controlled reason and bounded public CAP document ID, never raw exception text, source content or credentials. The public health exposes geometry issue counts and the safe failing document ID.

The compatible reader advertises `geometry_protocol: tmd-cap-geometry-v1`. The existing TMD Action now waits for that reader before collecting/publishing the new optional fields. Rollback remains the existing A/B product rollback; coordinate any rollback to an older application reader with a compatible stored feed.

## GISTDA page-size recovery and diagnostic limits

The old `RESPONSE_TOO_LARGE` came from a shared condition: either a page exceeded 8 MiB or total source bytes exceeded 768 MiB. The failed historical response body and separate counters were not retained, so it is not possible to retrospectively prove which branch caused that run. The 6 November pre-change daily run had already recovered all three windows (0 / 48,866 / 127,299). This increment prevents an oversized individual page from automatically ending an otherwise bounded query and makes future causes distinguishable.

The collector starts at 1,000 requested records. If a page exceeds 8 MiB, it closes that response, discards the unaccepted page and retries the **same offset** with limits 500, 250, 125, then 100. It advances the offset only after accepting and validating the complete page. After two accepted pages below one quarter of the byte ceiling it can raise the page limit by one step. All downloaded bytes and attempted requests, including abandoned oversized pages, remain charged to the original budgets.

Provider totals must remain constant. Duplicate/repeated source identities, invalid source metadata, unknown CRS, canonical membership/geometry failures and incomplete pagination remain fatal. Source features are not simplified, dropped or merged. Record IDs, original coordinates, query/acquisition uncertainty, independent 3/7/30-day products and the default national 3-day view remain unchanged.

Budgets remain 8 MiB per accepted page, 768 MiB source bytes per window, 250 attempted pages per window, 300 source requests shared by the three windows, the existing 20-minute per-window/45-minute shared collection deadlines, and the existing feature/position/normalized/chunk/storage guards. Adaptive pagination can still stop safely if these limits are reached; it does not guarantee arbitrarily large queries will fit.

New controlled failure reasons distinguish `SOURCE_PAGE_RESPONSE_TOO_LARGE` (even at minimum page limit), `SOURCE_RESPONSE_BUDGET_EXCEEDED` (total bytes), and `SOURCE_PAGE_BUDGET_EXCEEDED` (attempt allowance). Diagnostics record numeric requests, completed pages, resized pages, source bytes, largest page bytes and failing offset/limit/page bytes. Successful metadata includes the actual accepted `page_limits`; `query.limit` remains the initial maximum request limit. Page-limit counts and returned-source accounting are validated in Python and TypeScript. Failed candidates never replace the current product.

The public compatible reader advertises `collection_protocol: gistda-adaptive-pages-v1`; the existing waiting collector now requires it. No provider request is made by website traffic. No new account, paid resource, secret, scheduler, or workflow was created.

## Verification

The real public CAP feed was recollected locally: **5 listed items, 5 retained messages, 1 geometry issue**. All 73 original polygon strings of the affected message are preserved. A Python-produced golden feed is checked by the TypeScript reader. Local browser verification showed both current/previous messages, the original affected warning text/times/codes and the explicit missing-outline explanation; console errors were zero.

Regression tests exercise exact-offset retry with unchanged final geometry hashes, aggregate-byte and minimum-page failures, charging discarded requests to shared/per-window allowances, and changed provider totals after a retry. CAP regressions cover original malformed coordinates, unclosed and crossed rings, source retention, rejection of forged geometry qualifications, publication/rollback and whole-feed failure for invalid document metadata. The historical malformed CAP file is a fixture, never a production fallback.

Local validation: **354 Python tests**, **135 web tests**, TypeScript and production build passed. Running-app and production receipts are appended after publication verification.
