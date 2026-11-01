# Radar, QPE and nowcasting source review

Reviewed 1 November 2026, Asia/Bangkok. C0 discovery is complete for this increment. **None of these candidates is accepted as a production product yet.** The seven connected products are unchanged. Public HTTP responses and source code are evidence, not instructions or permission to reuse credentials.

## TMD national composite

The [old QPE index](https://cmmet.tmd.go.th/radar/Radar_compo.html) points to `compositeQPE_VTBB_latest.asc.zip`; that link returned 404. The current [TMD composite monitor](https://weather.tmd.go.th/composite/index_composite.html) provides working image, ASCII and NetCDF links instead.

| Candidate | Verified sample | Acceptance gap |
| --- | --- | --- |
| Composite rain-rate images | `images_composite.list` returned 25 frames at 15-minute intervals, 04:15–10:15 on 2026-11-01. The viewer interprets timestamps as UTC. `radar.sharing.latest` matched 10:15. The latest listed `images/zr/24.png` returned HTTP 200, 1800 × 2644 RGBA. Viewer corners, longitude/latitude order: (95,22.5), (108,22.5), (108,4), (95,4). The displayed scale is mm/hour; the page describes a PCAPPI Z–R product. | The geographic rectangle does not certify radar coverage at every pixel. Alpha/no-echo/no-coverage semantics, exact raster alignment, legend thresholds and refresh/availability history need verification. Numbered image URLs are mutable; a future collector needs a coherent, bounded generation capture rather than inventing times from frame position. |
| Numerical composite ASCII | HTTP 200, advertised 21,380,415 bytes; only the first 65,536 bytes were captured. Header: 1301 columns, 1851 rows, xllcorner 95, yllcorner 3.99, cell size .01, nodata −9999. | Header has no units, product timestamp or explicit CRS declaration. Do not infer accumulated QPE from the filename or render this as mm/24h. Full payload and grid registration have not been validated. |
| Numerical composite NetCDF | HTTP 200, advertised 9,658,896 bytes; bounded prefix contains the complete classic NetCDF header and coordinate arrays. COARDS, longitude/latitude in degrees, 1301 × 1851 grid, longitude 95–108, latitude 4–22.5. Reference date 2026-11-01 10:15 UTC. | The data variable is `var0_1_203_surface`, with placeholder `long_name: desc`, `units: unit` and fill value approximately 9.999e20. This does **not** establish its scientific quantity or accumulation period. ASCII lower-edge coordinates and NetCDF point coordinates need an explicit alignment check. Numerical values were not accepted or ingested. |

Direct public resources: [frame list](https://weather.tmd.go.th/composite/images_composite.list), [latest source clock](https://weather.tmd.go.th/composite/radar.sharing.latest), [ASCII](https://weather.tmd.go.th/composite/data/composite.ascii), [NetCDF](https://weather.tmd.go.th/composite/data/composite.nc). An observed 15-minute sample cadence is not a provider SLA or a configured freshness threshold.

## SATDA nowcasting

The [official SATDA page](https://satda.tmd.go.th/?r=site%2Findex) links several separate products. They cannot be combined into a claim of national nowcasting coverage.

| Candidate | Verified sample | Acceptance gap / decision |
| --- | --- | --- |
| Southern radar / SWIRLS viewer | [Viewer](https://satda.tmd.go.th/wp-content/uploads/data/dashboard/radar_map/south_nowcast.php), [manifest](https://satda.tmd.go.th/wp-content/uploads/data/dashboard/radar_map/leaflet_layers/layers.json), both HTTP 200. Manifest: 18 frames, 5 observations and 13 `swirls` forecasts; `now_index: 4`, base time `2026-11-01T09:45:00`; last forecast 13:00. Frame bounds are supplied. | Timestamps have no offset; `generated_at` also lacks one. Do not assign UTC or Bangkok time. The sampled horizon reaches 195 minutes after base time, which differs from the parent page's 180-minute description. A broad raster rectangle is not proof of valid coverage. Unit, no-data/coverage masks, exact forecast lead semantics and reuse rights remain unresolved. |
| Bangkok NEXTGEN / Tomorrow.io branch | [Viewer](https://satda.tmd.go.th/wp-content/uploads/nowcasting/bkk/bangkok.php), [manifest](https://satda.tmd.go.th/wp-content/uploads/nowcasting/bkk/bangkok_frames/manifest.json), HTTP 200. Explicit UTC frame times, precipitationIntensity field, geographic bounds and 23 frames. | Manifest was generated **24 June 2026**, months before this review. Reject as a current feed. The branch identifies Tomorrow.io; TMD hosting alone does not establish third-party redistribution rights. Other branches in the same viewer are separate candidates. |
| Khon Kaen / northeastern viewer | [Page](https://satda.tmd.go.th/wp-content/uploads/nowcasting/kkn/khon_kaen.php) returned HTTP 200 and describes a 60-minute regional nowcast. | Page reachability alone does not establish a current machine-readable feed, explicit UTC times, valid pixel coverage or a reusable product contract. Not accepted. |
| FY4B QPE on SATDA | Parent page exposes satellite QPE images. | This is satellite-derived, not radar QPE. Listed filenames included malformed calendar/hour strings. Do not normalize them into invented observation times; investigate as a separate source if pursued. |

## Terms, collection and next gate

[TMD's copyright page](https://www.tmd.go.th/content/copyright) describes attributed noncommercial republication of website content and qualifies accuracy and availability. It does not establish an unrestricted resource-specific data licence, automation quota, retention/redistribution grant or SLA for each raster and third-party branch above. No website keys, authenticated endpoints or AI proxy were used; no account, paid service, collector, schedule or public raster endpoint was created.

The recommended C1 candidate is the **TMD national composite image sequence**, after confirming reuse conditions and the pixel/coverage/time contract. A future adapter must keep observed rain rate separate from forecasts, accumulated QPE and station rainfall; preserve original frame times and hashes; reject mixed generations, invalid/future/stale frames, oversized payloads and unsupported formats; distinguish transparent/no-data from measured zero; and fail visibly without presenting missing frames as clear weather. An operational prototype can then verify alignment and outage behavior before a production player is enabled.

C3 remains pending a separately accepted nowcast product with explicit issue/valid times, lead time, coverage and rights. C4 station-to-area rainfall fill and dam photos remain deferred. No provider contact or permission request was sent.

Machine-readable HTTP evidence, bounded-capture hashes, NetCDF header and sampled manifest summaries: [review receipt](radar-source-review-2026-11-01.json). These are dated observations, not a guarantee that mutable provider URLs still return the same bytes.
