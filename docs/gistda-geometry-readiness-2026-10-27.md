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

Local verification passed **154 Python tests**, with **18 opt-in HTTP checks skipped**. Offline regression covers geometry validity, holes/multipolygons, invalid/self-intersecting rings, coordinate errors, complexity limits, hierarchy mismatches, synthetic secrets and full-client value redaction.

## Observed result

[Run 40514548736](https://github.com/tordave1150/hazard-intelligence/actions/runs/40514548736), job 122224942544, completed successfully on **9031729**. The API returned HTTP 200, one returned feature of **164,878** reported matches, response timestamp **2026-10-27T13:43:34.886Z / 27 October 20:43:34.886 ICT**. These are response time and query counts, not acquisition time or a national flood total. Three links were discarded. The result remains `FEATURE_PAGE_OBSERVED_SCHEMA_UNVERIFIED`.

The single inspected geometry was **MultiPolygon**, one ring/14 positions, passing syntax and topology checks; every checked coordinate was within the pinned Thailand bounding box. Source province and district codes matched known pinned identities and their parent relationship. No district filter was requested. The tambon prefix matched its district; tambon identity is not independently verified. All seven tested provider metadata fields were present, but their values were not logged. CRS/spatial accuracy, acquisition, units, coverage and display rights remain unverified. This is neither a one-day product nor a full 30-day snapshot.

The query's reported match count differs from the earlier 184,323 matches; it is a new response, not evidence that an equivalent area has drained or that the product is spatially complete. No change/impact inference or cross-page consistency claim is made. A future complete collector must handle the provider's update/pagination semantics explicitly.

CI [40514548677](https://github.com/tordave1150/hazard-intelligence/actions/runs/40514548677) passed both Python and web jobs; Vercel reported successful deployment for 9031729. A value-free receipt is saved locally in ignored `artifacts/gistda-quality-2026-10-27.json`. No raw feature or geometry was persisted, no Atlas write occurred, no public flood layer was activated, and no provider message was sent.

Reviewed request **2026-10-27-05** explicitly rechecks the original **one-day Ongkharak (`ap_idn=2604`)** product with the new diagnostic. It makes one GET only, independent of the 30-day sample; no fallback or inferred no-flood conclusion is permitted. Its later response will be recorded separately. Source registry metadata now discloses the one-sample technical checks and retains UNAVAILABLE production freshness, qualified CRS/units and the disabled layer.

## Acceptance still required

The [specific official one-day resource](https://opendata.gistda.or.th/th/dataset/flood-disaster-data/resource/062a08da-a6a9-4db7-9af7-1d345e38563a) was re-read on 27 October and still displays **License not specified**. The [API manual](https://disaster.gistda.or.th/manual_api.pdf) documents technical access; it does not resolve the dataset's public-display/redistribution terms or the observed field meanings. Privacy-policy search results were not treated as a dataset license. No agency message has been sent or additional account terms accepted on the user's behalf.

Before a public production adapter, confirm resource-specific display/retention terms, actual acquisition/temporal semantics, area units if area metrics are included, provider CRS/quality/coverage, quota and a consistent bounded complete-retrieval method. Source-specific time/quality gaps must remain explicit. The [saved Thai provider questions](GISTDA_DISASTER_PRODUCT_QUESTIONS_TH.md) remain available for the user's later action.
