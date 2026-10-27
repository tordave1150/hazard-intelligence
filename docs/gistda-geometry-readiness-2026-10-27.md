# GISTDA geometry and identity readiness — 2026-10-27

The user selected GISTDA as the next development priority. Technical work has resumed; the provider-question draft remains unsent. Public flood-data publication is not accepted by this diagnostic.

## New bounded checks

`scripts/gistda_sample_quality.py` inspects the single returned Features sample in memory, after the existing fixed-host/header-authenticated client validates the envelope. It returns fixed classifications, counts and metadata-presence flags only. Coordinates, provider property values, creator identifiers, links and assets are neither logged nor stored. No geometry repair, reprojection, simplification, area calculation or data publication occurs.

- Polygon/MultiPolygon coordinate nesting, finite numbers (excluding booleans), 2D/3D positions, closed rings and longitude/latitude ranges are checked against [RFC 7946](https://datatracker.ietf.org/doc/html/rfc7946). At most 256 rings/20,000 positions proceed to bounded topology validation. Legacy `crs` members require review. Clockwise source rings are preserved, consistent with the RFC's backwards-compatible parsing guidance.
- Shapely checks nonempty valid topology without logging GEOS error messages or invalid coordinates. The output distinguishes structurally/topologically valid geometry from independently verified provider CRS, spatial accuracy and observation coverage. A comparison with the pinned Thailand bounding box is a diagnostic only; it does not prove location accuracy or clipping to administrative boundaries.
- Exact province/district codes are compared to the project's pinned DOPA directory, including their parent relationship and any requested district. Numeric integers and exact strings are supported; float rounding, booleans and unknown identities are rejected. Tambon checks cover only six-digit format/parent prefix, not tambon identity. Registry currency remains qualified by its 2023-09-01 source date.
- Presence of `_createdAt`, `_updatedAt`, `file_name`, `_area`, `f_area`, `h3_area` and `rice_area` is reported without exposing values. None supplies an accepted acquisition date or unit. Metadata/file names are never converted into acquisition time, area totals, impact counts or all-clear statements.

The diagnostic always returns `public_layer_ready: false`, with acquisition time, area units, coverage semantics and public-display permission UNVERIFIED. A successful diagnostic means the checks ran, not that the flood product passed scientific or permission acceptance.

## Explicit real-data request

Reviewed request **2026-10-27-04** selects **Features, 30days, no administrative filter, limit=1, offset=0**. This separately labelled product previously supplied a nonempty sample; the new inspection addresses geometry and administrative consistency not exposed by earlier structure-only reports. It does not substitute for the one-day product or claim complete national collection. The main-only request-path trigger uses the existing GitHub secret, makes one GET, does not paginate or follow returned links, and receives no database credentials. No schedule is added.

Execution evidence will be recorded after the reviewed main request runs. Local verification passed **154 Python tests**, with **18 opt-in HTTP checks skipped** because this change does not modify the web application or public API. Offline regression covers geometry validity, holes/multipolygons, invalid/self-intersecting rings, coordinate errors, complexity limits, hierarchy mismatches, synthetic secrets and full-client value redaction.

## Acceptance still required

The [specific official one-day resource](https://opendata.gistda.or.th/th/dataset/flood-disaster-data/resource/062a08da-a6a9-4db7-9af7-1d345e38563a) was re-read on 27 October and still displays **License not specified**. The [API manual](https://disaster.gistda.or.th/manual_api.pdf) documents technical access; it does not resolve the dataset's public-display/redistribution terms or the observed field meanings. Privacy-policy search results were not treated as a dataset license. No agency message has been sent or additional account terms accepted on the user's behalf.

Before a public production adapter, confirm resource-specific display/retention terms, actual acquisition/temporal semantics, area units if area metrics are included, provider CRS/quality/coverage, quota and a consistent bounded complete-retrieval method. Source-specific time/quality gaps must remain explicit. The [saved Thai provider questions](GISTDA_DISASTER_PRODUCT_QUESTIONS_TH.md) remain available for the user's later action.
