# Thailand map context, existing rivers and individual dam symbols

Implemented 1 November 2026 (Asia/Bangkok): the next accepted usability increment, A4, A5 using existing basemap data, and A1/A2. This does not complete the remaining layer architecture or radar roadmap.

## Thailand focus and rivers

The display-only Thailand outline/outside mask is derived reproducibly by `python -m scripts.build_map_context` from the existing 77-province display geometry. The source bytes match the committed canonical input. Topology-preserving 0.008-degree simplification changes planar display area by approximately 0.03%; the bounded output is 143,213 bytes. It is a basemap context asset, never a legal boundary, selectable administrative area, source-membership boundary or scientific area metric. The [geometry receipt](map-context-geometry-2026-11-01.json) records hashes and attribution. Canonical areas, province/district files and basin memberships are unchanged.

An outside shade and country outline use owned context layers below data products. Only captured basemap IDs receive background paint changes. Low-zoom foreign place labels/icons fade using their position relative to the derived country polygon, rather than an assumed country-code field. Road prominence is reduced at low zoom and returns when zooming in. Theme changes do not recolor weather metrics, CAP, GISTDA or station products. Map-control hover colors also follow all four themes.

Actual OpenFreeMap vector tiles were inspected before choosing a river implementation. The reviewed z4 tile contained ten generalized river lines; z5 samples contained zero to five each. A z8 sample included named Yom, Nan and Ing river features. Existing `waterway` line color/width now emphasizes `class=river`, while minor waterways appear at closer zooms. Width is based on source class and zoom, not an invented stream order. Existing river-name labels retain their zoom-10 minimum. The [tile receipt](waterway-context-review-2026-11-01.json) records these samples. Tile generalization is not a complete inventory or a guarantee that every named Thai river is visible nationally. No HydroRIVERS import, new provider request schedule, hydrological network or station-to-river linkage was added. Existing OpenFreeMap/OpenMapTiles/OSM attribution remains visible.

## Dam symbols

All 35 RID reports have individual markers at their original published points, including national view. Regional/basin count circles and their centroid positions are retired. Markers have a consistent size within each zoom class: 26px nationally, 34px locally. Nearby points can overlap; all 35 remain independently reachable through the existing reservoir list and keyboard controls. Selection raises the marker and zooms to at least z9; changing 2D/3D preserves the selected dam focus. Native DOM markers remain billboards with terrain enabled.

The SVG dam pictogram has a ring showing `storage_pct`, the fraction of **normal storage capacity**. Only the ring saturates at 100%; the original percentage remains in the label, tooltip and details. Values above 100% have `+`; missing percent has a dashed track and `?`; measured zero is distinct. No marker-size encoding uses maximum capacity. Delayed/stale/unknown time qualifications use gray, with a small local clock indicator. Colors and ring fullness are not danger levels, water elevation or flood depth.

## Verification

- Python: 267 passed. Canonical-geometry coverage still checks all 1,033 selectable polygons (1,011 administrative and 22 basin); separate tests validate the non-selectable context mask.
- Web: 76 passed, including four-theme restrictions on captured base IDs, class-based river styling and null/zero/above-100% ring semantics. TypeScript and optimized production build passed.
- Local HTTP contracts: 24 passed. The temporary visual-review route was archived under ignored artifacts and removed before production build.
- Browser: actual Dawn/Day/Dusk/Night captures at national and Chiang Mai province scale. Each national case had 35 dam markers and no dam clusters; each province case had two original points. Source values and capacities remained explicit. The province is a QA example, not a preferred area/default.
- Responsive 390x844: all four themes retained 35 markers and equal document client/scroll widths of 375px (native scrollbar). The national list exposed all 35 report buttons. The real 109.62% report retained that value with `+`; another real 68.08% report preserved 179.06 million m³, normal capacity 263 and maximum capacity 295 in 2D/3D. Browser console errors/warnings and map error banners were zero in the reviewed flow.

Four-theme QA used a temporary local clock control without changing source timestamps. Early review clocks correctly qualified later retrievals as UNKNOWN; dusk/night qualified the same-date RID capture as FRESH. These are local visual-review states, not production source-age claims. The ordinary route was separately checked with the real clock after the harness was removed. Proof images and the review harness are in ignored `artifacts/context-dams-*` files.

Production deployment, API availability and real-clock browser checks are verified separately after publication. Runtime-log access was previously unavailable through the connected Vercel account (403); HTTP/console evidence does not certify an absence of server-side log errors.
