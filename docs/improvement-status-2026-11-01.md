# Improvement proposal implementation status

Updated 4 November 2026, Asia/Bangkok. This tracks accepted increments against the user's proposal; it is not a claim that the entire proposal is implemented.

| Part | State | Evidence / remaining scope |
| --- | --- | --- |
| A3/A6 station clusters and legend | Shipped | [Legend release](map-legibility-release-2026-11-01.md), separate water/rain record counts and mobile source notes |
| A4 Thailand focus | Shipped | [Context/dam release](map-context-dams-release-2026-11-01.md), four-theme local review and real-clock production receipt |
| A5 rivers | Existing-basemap increment shipped | Actual low-zoom tile review, class/zoom styling, existing names at z10+; no claim of complete national river detail or new river dataset |
| A1 individual dams | Shipped | All 35 original points/list entries; no centroid/count-circle navigation; nearby markers may overlap |
| A2 dam icon/ring | Shipped | Percent of normal capacity, null/zero distinction, original >100% value, uniform size within zoom class, 2D/3D |
| B layer architecture | Shipped | [Background/ordering release](map-layers-release-2026-11-01.md); single forecast background, independent overlays, shared 2D/3D order; station rain remains points |
| C0 source acceptance | TMD image display accepted with explicit qualifications; other candidates pending | [Qualified TMD image acceptance](tmd-radar-acceptance-2026-11-04.md) covers PNG display only; numerical QPE remains unqualified. [Nowcasting recheck](nowcasting-review-2026-11-04.md) establishes southern filename UTC/dBZ but records duplicate and out-of-horizon frames |
| C1 radar image player | Shipped; quota follow-up implemented | [Image release](radar-release-2026-11-04.md), [operations follow-up](radar-operations-2026-11-04.md): half-hour samples, reuse, conservative upload reservations and preserved failure stages |
| C3 nowcasting | Blocked at source acceptance; read-only inspector added | [Current receipt](nowcasting-review-2026-11-04.json); southern issue time/coverage/reuse remain unqualified, Bangkok and Khon Kaen candidates are old. No forecast publication |
| C2 station rainfall | Already connected before this proposal increment | [Rain/province/basin release](province-rain-basin-release-2026-10-30.md); radar QPE remains separate and unconnected |
| C4 rainfall polygons | Deferred | No station-to-province rainfall fill without an accepted method |
| D dam photos | Deferred | Per-image permission/attribution review still required |

Further map fit and mobile/layout work is explicitly deferred by the user to a later combined pass. Existing release screenshots are historical verification, not evidence of new layout work in this increment.
