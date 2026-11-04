# Nowcasting acceptance recheck

Read-only check on 4 November 2026, 15:04 UTC / 22:04 ICT. [Machine receipt](nowcasting-review-2026-11-04.json) records URLs, byte sizes, SHA-256 and findings. These are observations of one retrieval, not a provider availability guarantee. No forecast images were copied to Blob and no nowcasting product was enabled.

## Southern TMD RaINs / SWIRLs branch

The [official viewer](https://satda.tmd.go.th/wp-content/uploads/data/dashboard/radar_map/south_nowcast.php) explicitly parses the twelve-digit filename with `Date.UTC` and uses that value for the displayed frame. Its legend is dBZ, a reflectivity display, separate from the existing C1 mm/hour radar-estimate product. This resolves the earlier uncertainty about **valid filename time** for this branch; it does not establish a qualified forecast issue/creation timestamp.

The [current manifest](https://satda.tmd.go.th/wp-content/uploads/data/dashboard/radar_map/leaflet_layers/layers.json) has five observation frames and seventeen `swirls` entries, base observation 14:00 UTC. Its forecast leads are +30 through +195 minutes, followed by **five entries referencing the identical `202611042145.png`**, each +465 minutes under the viewer's explicit UTC rule. The inspector records duplicate names, nonincreasing valid times and times outside the advertised 180-minute horizon. Do not remove duplicates or reinterpret those times as ICT to manufacture an apparently valid forecast cycle.

`generated_at: 2026-11-04T21:54:45` has no offset. Preserve it as raw text; do not treat it as UTC, ICT or the forecast issue time. The broad image rectangle is not proof of valid national radar coverage. The viewer separately loads a southern 240-km coverage geometry and contains another Tomorrow.io-based branch; acceptance must isolate provenance and reuse rights per branch. A future forecast collector also needs its own image volume budget; seventeen new forecast images per cycle would exhaust the current radar-only allocation quickly.

Acceptance remains blocked by the observed frame/time defects, qualified issue time, validated coverage/no-data behavior, and branch-specific reuse/storage acceptance. No numerical dBZ/rainfall grid or district prediction is derived from this viewer.

A regional source can be accepted later with explicit, validated regional coverage. Thailand-wide application scope does not require every source to cover the whole country, and does not permit filling unknown areas outside its coverage.

## Other candidates

- [Bangkok manifest](https://satda.tmd.go.th/wp-content/uploads/nowcasting/bkk/bangkok_frames/manifest.json): explicit `generated_at` 24 June 2026 11:11:26 UTC, stale for the review date; `precipitationIntensity` and regional bounds. Third-party reuse is unresolved.
- [Khon Kaen viewer](https://satda.tmd.go.th/wp-content/uploads/nowcasting/kkn/khon_kaen.php): its listed filename times are 17–18 February 2026, while the page describes an updated regional 60-minute forecast. No qualified timezone or issue time is provided by the inspected listing. Do not relabel these as current nationwide data.

## Repeatable check

`python -m scripts.inspect_nowcasting --export artifacts/nowcasting-review.json`

The tool fetches only four fixed public text endpoints, rejects redirects and oversized documents, and records an inspection result rather than publishing. It checks frame grammar, valid UTC convention, ordering, duplicates, source counts, base alignment, age and the 180-minute horizon. Even a structurally valid manifest remains unaccepted while issue time, actual valid coverage/no-data and reuse/storage gates are outstanding. Synthetic tests exercise each rejection and preserve generated/issue-time uncertainty. Other application sources remain unchanged.
