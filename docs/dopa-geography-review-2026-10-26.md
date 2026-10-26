# DOPA directory comparison — 26 October 2026

The official [BORA/DOPA code-directory page](https://stat.bora.dopa.go.th/stat/statnew/statMenu/newStat/ccaa.php) links [ccaatt.xlsx](https://stat.bora.dopa.go.th/dload/ccaatt.xlsx). The downloaded workbook explicitly says **ข้อมูล ณ วันที่ 1 กันยายน 2566** (1 September 2023). Its HTTP Last-Modified is 2 October 2023. Fetching it in 2026 does not make its reference date 2026.

SHA256: `5977e39e689d229668dabb2ff47f1a1a4bec341bd1efa0792cb45cad8e16d6e9` (374,371 bytes). The original workbook and discovery page remain ignored under `artifacts/source-review-2026-10-26/`; no population or personal records were requested. The committed correction manifest contains only the factual code/name differences needed by this project.

The directory documents the eight-digit province/district/subdistrict/village structure and marks cancelled codes with an asterisk. The workbook also provides a cancellation date. The audit accepts only active province/district rows (`D=0`, no asterisk), excludes subdistricts, and compares code sets, Thai names and province-parent prefixes. Bangkok's leading `เขต` is ignored only when comparing Bangkok district names.

Before correction, all 77 province codes matched, while one of 928 district codes differed:

| Area | Pinned boundary source | Official directory |
|---|---|---|
| เวียงเก่า / Wiang Kao, Khon Kaen | 4026 | 4029 |
| หว้านใหญ่ | ว่านใหญ่ | หว้านใหญ่ |
| เมืองประจวบคีรีขันธ์ | เมืองประจวบคีรีข | เมืองประจวบคีรีขันธ์ |
| เมืองนครศรีธรรมราช | เมืองนครศรีธรรมร | เมืองนครศรีธรรมราช |
| เมืองสุราษฎร์ธานี | เมืองสุราษฎร์ธาน | เมืองสุราษฎร์ธานี |
| ป่าพะยอม | ป่าพยอม | ป่าพะยอม |
| กรงปินัง | กรงปีนัง | กรงปินัง |

After applying the small versioned manifest in `data/geography/dopa-corrections.json`, the project matches **77/77 provinces and 928/928 districts**, with no missing/extra codes, Thai-name differences or invalid parents. The reproducible machine report is [dopa-directory-audit-2026-10-26.json](dopa-directory-audit-2026-10-26.json).

## Snapshot compatibility

The geometry builder applies the correction before writing metadata and per-province display geometry. Original attributed raw inputs remain byte-for-byte unchanged. English transliterations, every polygon, bounding box and representative coordinate remain unchanged. Weather collection still requests exactly 1,005 points.

Existing weather generations can contain `TH-D-4026`. At read time only that exact historical ID at the original requested coordinate (16.725377, 102.291901) maps to `TH-D-4029`. The API reports the applied mapping in `identity_migrations`. Values, periods, model point and retrieval/ingestion times are preserved; no database rewrite or provider fetch occurs. A point mismatch or old/new identity collision fails validation. New complete ingestion uses only `TH-D-4029`; the two-slot 2,010-document bound is unchanged. Read-only database verification applies the same narrowly bounded compatibility mapping and reports its count without writing records. This also permits reading an intact old generation after an authorized data rollback.

## Reproduce

Download the workbook through its official directory link, then run:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.audit_dopa_geography --input <saved-ccaatt.xlsx> --check
.\.venv\Scripts\python.exe -X utf8 -m scripts.prepare_geography
```

The audit has no network operation and pins the exact reference checksum. A changed official workbook must be reviewed before updating the pin. It never silently adopts a new upstream identity set.

## Limits

This closes the independent code/name comparison against the **official downloadable 2023 table**. It does not certify that table's currency through October 2026, the legal accuracy of the separate OpenGISData display boundaries, or a legal cadastral survey. Current registry changes after September 2023 and authoritative boundary comparison remain explicit release limitations. The six-region project grouping is not changed by this audit.
