# Desktop map workspace

6 November 2026, Asia/Bangkok. Implements the desktop structural increment of the supplied visual redesign brief against baseline `1c86f670c182c0b7ec7828500384100faa6c16e1`. This is not a claim that every phase of the brief is finished. The source video was not supplied; no pixel-match claim is made.

The operational map now occupies the initial viewport. The large introductory title and four permanent summary cards are replaced by a compact header and an optional Overview dialog. The existing 77-province comparison retains its filters, sorting, provenance and source qualifications inside a dialog. Search supports Thai/English/canonical IDs and keyboard selection.

## State and control ownership

- Dashboard retains all source requests, polling intervals, snapshot health, immutable flood generations, source windows, viewport budgets and layer booleans. New components under `components/workspace/` own presentation, search, dialogs, pane navigation and the time dock. Styling is in a scoped CSS module; no new packages or map engine.
- Layers are independent observation checkboxes. Enabling several leaves the controls open. Rail tools select Layers or Geography; the contextual inspector shows exactly one Area, Forecast, CAP, GISTDA, Dams, Water or Rain context. Feature selection opens its source without clearing unrelated overlays. Disabling the active source falls back to Area.
- The dock is the single calendar/background selector. Today returns to Situation; +1/+2/+3 select daily forecast. Today's daily/hourly forecasts remain explicit alternatives. Hourly and observed radar are offered on Today only. A calendar action does not alter source overlay booleans, GISTDA windows/generations or the stored selected radar frame/hour. Radar retains its original player, clocks, load status, colors, opacity and no-data warnings.
- The map stays mounted at the same position when panes change. ResizeObserver follows container width changes and is disconnected on cleanup. Camera fit/pan/zoom/terrain algorithms and scientific layer ordering are unchanged.
- Active badges keep source query freshness, unknown observation/acquisition time, CAP geometry qualifications, dam report date and GISTDA viewport status visible with the inspector closed. Expanded notes retain the full source disclosures. An empty 3-day query does not become an all-clear or an automatic 7/30-day fallback.
- Interface surfaces follow the existing automatic Dawn/Day/Dusk/Night clock. Secondary text uses a stronger theme-derived contrast. Semantic hazard colors and map data palettes are unchanged. No synthetic clouds, weather or new paid services.

## Desktop verification

Baseline review at 1280×720 measured the map starting at y596, following the title/mode/summary blocks; only 124 vertical map pixels were initially visible. This was a vertical-density finding, not proof of overlapping controls.

Post-change browser DOM measurements with the water/rain/dam layers enabled, panes closed and background off:

| Viewport | Canvas container | Top/bottom, CSS px | Document size |
| --- | --- | --- | --- |
| 1366×768 | 1268×459.4 | 192.6 / 652 | 1366×768 |
| 1440×900 | 1342×591.4 | 192.6 / 784 | 1440×900 |
| 1920×1080 | 1822×771.4 | 192.6 / 964 | 1920×1080 |

At 1366px, opening the 350px inspector changed the canvas width from 1268 to 918px; canvas and container widths matched after resize. These are measured layouts, not screenshots or a performance benchmark.

Browser interaction checks exercised all five overlay toggles concurrently; CAP qualification disclosures; switching to a dam from its keyboard-accessible marker; keyboard search to a province/district; future-date daily selection with radar/hourly disabled; one hourly interval selector; all 77 province rows; Escape/focus restoration; and all 22 basin choices with future dates disabled. Source layers stayed enabled during date and inspector changes.

Theme checks inspected computed interface colors at injected local QA times for all four themes. The temporary clock was restored before build; production uses Date.now. Real stored radar frames retained original SHA-256 and clocks in ignored local files; a matching local QA clock exercised successful image loading and previous-frame navigation in 3D. At the real clock the same old images were correctly hidden as STALE. The local hourly sample covered one actual province and all original 24 intervals, explicitly LOCAL PREVIEW; it is not a national production fixture.

Screenshot capture timed out on both the unchanged production site and the local implementation in this browser session. Pixel-level visual comparison, animation/GPU benchmarks, responsive/mobile work and map-fit refinement remain outside the verified increment. No screenshot artifact is claimed.

Local validation: 140 web regression tests passed. Production build includes TypeScript validation. Release and production HTTP results are recorded after deployment.
