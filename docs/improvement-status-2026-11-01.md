# Improvement proposal implementation status

Updated 5 November 2026, Asia/Bangkok. This tracks accepted increments against the user's proposal; it is not a claim that the entire proposal is implemented.

| Part | State | Evidence / remaining scope |
| --- | --- | --- |
| A3/A6 station clusters and legend | Shipped | [Legend release](map-legibility-release-2026-11-01.md), separate water/rain record counts and mobile source notes |
| A4 Thailand focus | Shipped | [Context/dam release](map-context-dams-release-2026-11-01.md), four-theme local review and real-clock production receipt |
| A5 rivers | Existing-basemap increment shipped | Actual low-zoom tile review, class/zoom styling, existing names at z10+; no claim of complete national river detail or new river dataset |
| A1 individual dams | Shipped | All 35 original points/list entries; no centroid/count-circle navigation; nearby markers may overlap |
| A2 dam icon/ring | Shipped | Percent of normal capacity, null/zero distinction, original >100% value, uniform size within zoom class, 2D/3D |
| B layer architecture | Shipped | [Background/ordering release](map-layers-release-2026-11-01.md); single forecast background, independent overlays, shared 2D/3D order; station rain remains points |
| C0 source acceptance | TMD image display accepted with explicit qualifications; numerical QPE remains unqualified | [Qualified image acceptance](tmd-radar-acceptance-2026-11-04.md) covers PNG display only. [5 November bounded NetCDF header](tmd-netcdf-review-2026-11-05.json) still gives the numerical variable placeholder `units: unit`, `long_name: desc` |
| C1 radar image player | Shipped; quota follow-up implemented | [Image release](radar-release-2026-11-04.md), [operations follow-up](radar-operations-2026-11-04.md): half-hour samples, reuse, conservative upload reservations and preserved failure stages |
| C3 nowcasting | Source acceptance remains pending after recheck | [5 November receipt](nowcasting-review-2026-11-05.json): sampled duplicate names are gone, but +195-minute lead, unqualified issue time/valid coverage/reuse remain; Bangkok and Khon Kaen candidates are old. No forecast publication |
| C2 station rainfall | Already connected before this proposal increment | [Rain/province/basin release](province-rain-basin-release-2026-10-30.md); radar QPE remains separate and unconnected |
| C4 rainfall polygons | Deferred | No station-to-province rainfall fill without an accepted method |
| D dam photos | Deferred | Per-image permission/attribution review still required |

Further map fit and mobile/layout work is explicitly deferred by the user to a later combined pass. Existing release screenshots are historical verification, not evidence of new layout work in this increment.

The separate [GISTDA storage/history increment](gistda-window-release-2026-11-05.md) is deployed: disk-spooled national 3/7/30-day products, compressed storage, query archives and bounded area display. The [production receipt](gistda-window-production-2026-11-05.json) records 0 / 50,219 / 132,962 returned records, a successful complete payload audit, 326 Python tests, 124 web tests and 29 production HTTP checks. It preserves unknown current flood state and does not convert historical water evidence into a new observation. Actual query history starts with retained snapshots, and the compressed storage guards can reject future larger candidates. Radar automatic scheduling has executed, but continuous 30-minute delivery remains unproven; cleanup of two empty Blob stores still requires dashboard access. Numerical QPE and nowcasting retain the source-acceptance gates above.
