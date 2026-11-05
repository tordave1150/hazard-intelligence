# Flood viewport loading and precipitation source review

5 November 2026, Asia/Bangkok. This increment implements items 3–4 of the accepted follow-up. Map fit, responsive layout and mobile work remain deferred.

## Flood map behavior

GISTDA's default remains the national retrospective 3-day product, with explicit independent 7/30-day products. The map now defaults to **ตามบริเวณที่มองเห็น**. Wide views retain national/administrative summary counts and ask the user to zoom. After movement settles, a debounced request loads original records whose exact feature bounding boxes intersect the view and whose administrative membership matches the selected area. Bounding-box intersection can overinclude a polygon; it is not polygon clipping, valid satellite coverage or flooded-area estimation.

The request pins window, retained query UUID, selected area and bounding box. The client also checks the original retrieval clock and source count. Cancelling movement, changing a window, query or area clears old geometry and aborts obsolete requests. Nothing infers a new satellite acquisition, safe conditions or continuing flooding from query freshness. A zero result remains an empty retrospective result.

`/api/flood-products/viewport` accepts only those fixed parameters. A view wider than 4 degrees or over 512 candidate index chunks asks for a closer zoom. Otherwise it reads small per-feature bounding-box indexes first, then at most 64 matching original geometry chunks in cursor batches of four. Display is bounded to 2,000 original records and 4 MiB of record JSON. Every limit is explicit: partial results report the matched count and invite zooming or area browsing. The independent **รายการของพื้นที่ที่เลือก** mode preserves the previous area summaries and manual 100-record district pages. There is no silent fallback to a country geometry download.

## Derived index, source preservation and capacity

The collector builds a deterministic gzip/MessagePack bounding-box object for each immutable original geometry chunk. The original feature coordinates, precision, IDs, duplicate geometries, order within each source chunk, counts, query clocks and acquisition uncertainty are preserved. Index hashes, lengths, count and union bounds are checked; deep verification compares every indexed box with the original geometry.

New collections publish indexes before the manifest/control pointer. `python -m scripts.mongo_admin index-flood` adds indexes to retained existing queries under the publication lock, without querying GISTDA or changing any feed, geometry object, query UUID or control pointer. The public compatible reader must be deployed before maintenance starts. Failure before manifest promotion leaves the original query usable. A legacy unindexed query is explicitly unavailable in viewport mode and remains readable in area mode.

Auxiliary compressed indexes have a 32 MiB guard and also count toward the existing 320 MiB shared object pool and 400 MiB logical database guard. Original per-query geometry remains bounded to 128 MiB. Index cache charge is bounded to 8 MiB per server process; manifest caches retain their existing bounds. These are application guards, not a claim about a billing plan, physical allocated storage or provider capacity.

## Item 4: recheck and visible qualification status

The Sources page now has a separate dated review with official links; the eight registered sources and accepted radar image player remain unchanged. Regional nowcasting is eligible once its scientific, time, coverage and reuse contract is accepted; nationwide forecast coverage is not required to accept a clearly labelled regional product.

The [SATDA Southern viewer](https://satda.tmd.go.th/wp-content/uploads/data/dashboard/radar_map/south_nowcast.php) recheck at 20:36 ICT found 18 frames: five observations, thirteen forecasts at +15 through +195 minutes, dBZ display and no duplicate sampled filenames. Its viewer establishes the filename valid-time parser as UTC. The manifest's issue/generation wall time still lacks a qualified offset. +195 differs from the [parent site's](https://satda.tmd.go.th/) 180-minute description; valid/no-data coverage and reuse/storage acceptance also remain unresolved. Bangkok's sampled manifest is still dated 24 June; Khon Kaen's sampled frames are dated 17–18 February with unqualified timezone. No forecast images are published. See the [bounded machine-readable recheck](nowcasting-review-2026-11-05.json).

The [TMD NetCDF](https://weather.tmd.go.th/composite/data/composite.nc) and [ASCII](https://weather.tmd.go.th/composite/data/composite.ascii) check at 20:56 ICT read at most 65,536 bytes each, even when the server ignores Range. NetCDF reference time was 13:45 UTC, but the numerical variable still supplies `long_name: desc` and `units: unit`; the header cannot qualify a physical quantity or an accumulation period. The bounded prefix includes coordinate arrays. NetCDF points start at latitude 4 / longitude 95; a conventional interpretation of ASCII corners gives first cell centers 3.995 / 95.005. This is an **inference requiring provider confirmation**, not a declaration that either source is misregistered. No numerical values are ingested, shifted, resampled or converted into administrative rainfall. The independent image-display acceptance does not qualify these numerical grids. See [metadata and alignment evidence](precipitation-review-2026-11-05.json).

Reproduce read-only reviews with `python -m scripts.inspect_nowcasting --export artifacts/nowcasting-review.json` and `python -m scripts.inspect_precipitation --export artifacts/precipitation-review.json`. The next acceptance step needs resource-specific clarification of issue time/horizon/valid coverage/reuse for nowcasting, and quantity/units/accumulation/grid registration/no-data/reuse for numerical precipitation. No external message or permission request was sent.

## Verification

Local browser checks used explicitly labelled synthetic fixtures: an empty 3-day query, independent 7/30-day counts, a 3,001-record dense viewport limited to 2,000 with a visible partial message, then a zoomed 864-record complete view. Movement clears old geometry; query/window changes are pinned. Explicit area mode retains 100-record pages. Browser console had no errors. Source geometry and scientific meaning remain unchanged.

Production verification and final test results are recorded separately after the compatible reader and derived indexes are deployed.
