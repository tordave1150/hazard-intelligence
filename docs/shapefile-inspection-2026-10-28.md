# Supplied flood shapefile: offline inspection — 28 October 2026

The user added `rd2_20261003_0608.zip` after implementation of the inspection tool. The real archive was read in place, without extraction, geometry export, source modification, network requests or public ingestion. It is a separate offline input, not evidence for the live Disaster Features `1day` product.

Source SHA-256: `6dc4997a1b32c629cb4f130ee977269391ad3e63eefcb6bdceaea5a9f18cf14c`.

## Reproduced findings

| Check | Actual result |
|---|---|
| Archive/pairing | Passed bounded ZIP checks and SHP/SHX/DBF/PRJ offsets/counts |
| Shape records | 1,306 Polygon records |
| Source positions | 2,742,629 |
| Unique supplied codes | 32 provinces, 188 districts, 1,306 tambons |
| Province/district hierarchy | All 1,306 match the project's pinned directory |
| Tambon | All prefixes match their districts; tambon identity is not independently verified |
| Final `.prj` | EPSG:4326 |
| XML lineage | Mentions EPSG:32647; this does not override final file CRS |
| Empty/nonfinite geometry | 0 / 0 |
| Exact OGC geometry duplicates | 0 |
| OGC/GEOS topology | 876 records reported `Ring Self-intersection`; 430 did not fail that validation |
| `house` | Zero in all 1,306 records; impact/missing-value meaning remains unknown |
| Area relationship | All 1,306 satisfy the numeric hypothesis `flood_area = F_AREA / 1600` within the tested tolerance; provider business meaning/units are not thereby established |
| Acquisition/publication | No accepted acquisition/publication instant; filename time unverified, XML times are local processing lineage with unverified timezone |
| Original download / reuse rights | Unknown |

The topology result is specifically **GEOS/OGC validation after pyshp converts SHP rings into OGC geometry**. It is not a finding that every affected feature is unreadable, that its coordinates are wrong, or that an Esri validation has been run. Esri documents distinct Esri and OGC validation methods; we have not established the supplier's validation method. [Esri Check Geometry documentation](https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/check-geometry.html).

No repair was applied. A future derived product must evaluate repair effects on rings/holes, multipart structure and positional fidelity, document its method and validate again. Do not silently use `buffer(0)` or simplification as a scientific correction, or recalculate impact totals from unknown units.

## Integration decision

Keep this archive offline. Its 1,306 features already exceed the national collector's 1,000-feature application budget; its 2.74 million positions exceed the 100,000-position budget. The final CRS and code matches do not close topology, date, accuracy, clipping, provenance or permission gaps. Do not substitute it for an empty `1day` response or force it into an Atlas envelope.

A separate file/tile-backed historical product can be considered after provenance/reuse and temporal scope are established, with an evaluated geometry-normalization path. Administrative code membership does not prove correct boundary clipping or satellite coverage. No current national area or affected-house statistic is published from this file.

Reproducible command: `python -m scripts.inspect_flood_shapefile <external ZIP path> --output artifacts/<new report>.json`. Reports are kept in ignored local artifacts and contain metadata/counts rather than raw attributes or geometry. Real report: `artifacts/shapefile-real-final-report-2026-10-28.json`; the JSON includes library/GEOS versions and source hash. Tests use a separate synthetic archive and exercise corruption, traversal, escaped lineage and invalid polygons.
