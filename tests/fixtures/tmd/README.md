# TMD public CAP capture

The RSS index `feed-2026-10-26.xml` and its six linked `alert-0.xml` through `alert-5.xml` were retrieved from the Thai Meteorological Department on 26 October 2026. These are public Actual CAP messages, not synthetic current alerts. All six had expired before the retrieval date.

Attribution: **กรมอุตุนิยมวิทยา / Thai Meteorological Department**.

Source directory: https://www.tmd.go.th/service/rss . Feed: https://www.tmd.go.th/api/xml/CAP . The original CAP document URLs remain in the RSS capture. Feed copyright declares public domain; non-commercial republication with attribution is covered by https://www.tmd.go.th/content/copyright . See `docs/tmd-cap-acceptance-2026-10-26.md` for accepted scope and limitations.

These captures are test fixtures and are never a production fallback. Synthetic mutations for cancellation/current intervals/invalid input exist only inside isolated tests. Original wording and numeric coordinates are retained.

`alert-2026-10-28-invalid-interval.xml` was retrieved from the official CAP link on 29 October 2026. Its original effective time is 28 October 18:00 ICT and its expiry is 28 October 06:00 ICT. This provider conflict is preserved and explicitly flagged; no expiry correction is inferred. It verifies that one time-quality issue cannot stop a complete feed or appear as a current warning.

`alert-2026-10-27-unmapped-code.xml` was retrieved on 27 October 2026 from the official linked CAP document. It contains 31 source geocodes including `R-07` under the namespace `ISO3166-2`, plus 123 original polygon rings. This public source-quality case verifies that unknown codes remain verbatim while only 30 recognized provinces enter canonical area_ids; the code is not guessed to be a province or region. Its exact URL, retrieval time and SHA-256 are in the manifest. It is never a production fallback.
