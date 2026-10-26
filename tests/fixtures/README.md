# Public RID test capture

`rid-daily-2026-10-26.json` is an unmodified public daily-report response retrieved from the Royal Irrigation Department (RID), Thailand, on 26 October 2026. Source: https://app.rid.go.th/reservoir/api/dam/public . Documentation: https://app.rid.go.th/reservoir/api/document/dam .

Attribution: **ข้อมูลน้ำในอ่างเก็บน้ำ กรมชลประทาน (Royal Irrigation Department)**. The official dataset https://data.go.th/th/dataset/reservoir2 links to the same reservoir interface. Reuse terms: https://data.go.th/th/pages/dga-open-government-license . See `docs/rid-acceptance-2026-10-26.md` for the accepted scope and limitations.

The fixture tests decoding and validation. It is never served as production data. Its flow fields are preserved in the raw test capture but are not accepted by, exported from, or displayed by the daily-storage product. Synthetic mutations exist only inside isolated tests.
