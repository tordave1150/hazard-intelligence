# TMD public CAP capture

The RSS index `feed-2026-10-26.xml` and its six linked `alert-0.xml` through `alert-5.xml` were retrieved from the Thai Meteorological Department on 26 October 2026. These are public Actual CAP messages, not synthetic current alerts. All six had expired before the retrieval date.

Attribution: **กรมอุตุนิยมวิทยา / Thai Meteorological Department**.

Source directory: https://www.tmd.go.th/service/rss . Feed: https://www.tmd.go.th/api/xml/CAP . The original CAP document URLs remain in the RSS capture. Feed copyright declares public domain; non-commercial republication with attribution is covered by https://www.tmd.go.th/content/copyright . See `docs/tmd-cap-acceptance-2026-10-26.md` for accepted scope and limitations.

These captures are test fixtures and are never a production fallback. Synthetic mutations for cancellation/current intervals/invalid input exist only inside isolated tests. Original wording and numeric coordinates are retained.
