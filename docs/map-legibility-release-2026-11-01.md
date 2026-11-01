# Map legend and separate station cluster counts

Thailand-wide map usability update, 1 November 2026 (Asia/Bangkok).

## Behavior

- HII map clusters retain separate `water_count` and `rain_count` totals. Labels show `น้ำ` / `ฝน` with each product's exact record count, including mixed clusters. Co-located water and rain products do not become a unique-station total. Hover text explains the counting and click-to-zoom behavior. Neutral product colors are not danger thresholds.
- Enabled water, rain, RID, CAP and GISTDA overlays share a compact legend above the canvas. A keyboard-operable disclosure contains each source's dates, retrieval qualification and measurement meaning. Long notes wrap in normal page flow instead of overlapping at fixed map offsets. Forecast scales remain separate.
- Water MSL is not flood depth; station rainfall is not an administrative area average; RID percent is relative to normal capacity; GISTDA retains its retrospective three-day window and unknown acquisition time. The GISTDA count uses scope metadata while geometry loads, rather than implying an unloaded view has zero features.
- Mobile source/header text wraps. Layer choices survive 2D/3D switching. National collection, geography, source payloads, freshness calculations and scheduled workflows are unchanged.
- README, human/machine source registries and acceptance pointers now describe the seven connected products and separate 22-basin context. Old discovery evidence does not define current connection status.

## Local verification

The browser reviewed real public production snapshots in ignored local-preview files: 805 water-level records, 4,804 rain records, 35 RID reports, seven CAP messages and 803 GISTDA features. These are dated response counts, not fixed inventories. Original source timestamps were retained. During the 1 November review, old responses correctly displayed STALE and unknown observation age; no clocks were advanced to manufacture freshness. Preview files do not enter production bundles or replace production data.

- Python: 265 passed; the 24 opt-in HTTP cases were separately run against the local server and all passed.
- Web: 69 passed, including MapLibre expression evaluation for mixed and single-product clusters.
- TypeScript and optimized production build passed.
- Browser: all five overlays together; expandable source notes; water-only and rain-only selection; selected water point/history and rain detail preserved original values/units. No console errors or warnings were observed.
- Responsive viewport 390 x 844: document client/scroll widths both 375 px (native scrollbar), and all five source-note rows had equal client/scroll widths. Keyboard Enter collapsed the notes; all five enabled legend items remained after switching to 3D. No horizontal overflow.
- Visual review covered the current day theme and the prior night-theme preview. Four-theme clock selection remains covered by existing tests; dawn/dusk were not separately claimed as browser captures.

Local screenshots are under ignored `artifacts/map-legibility-*-2026-11-01.png`. Production deployment and production data availability must be checked independently after this change is released.

## Follow-up scope

Basemap contrast, river styling and a dam-icon prototype are a later usability increment. Radar/QPE/nowcasting require source-specific acceptance before ingestion or display. This release adds no unverified source or hydrological metric.
