# GISTDA pilot connection and warning-boundary repair

Started 2026-10-27 (Asia/Bangkok). Story: enabling Flood observations reads a bounded Atlas snapshot through `/api/flood-products`, opens the source panel and displays returned footprints or the genuine empty-query state. Browser requests never start ingestion. The initial product is **1day, Ongkharak ap_idn=2604 only**, not a nationwide flood-coverage claim.

## Warning outlines

The production check at 23:14 ICT found a 12-message TMD feed checked at 20:32, DELAYED after two hours. One message remained in its issued validity interval until 28 October 06:00 ICT. The old renderer filtered all default boundaries out unless the feed was FRESH, making delayed retrieval look like missing warning geometry.

Commit ea35986 keeps validity-window boundaries visible as **gray references** during delayed/stale retrieval. Agency orange/red still requires a fresh feed; selected expired/cancelled/superseded messages stay gray. TMD request 2026-10-27-02 succeeded in run 40539233290, refreshing the feed without changing warning issue/expiry times. The two-hour guard remains. The map badge now distinguishes delayed currency from a previous message.

## Connected GISTDA path

- `GistdaFloodFeed` preserves fixed product/filter, response/retrieval/ingestion times, complete-query counts and bounded Polygon/MultiPolygon coordinates. Footprints have generated IDs and `properties: null`. Raw provider properties, links and keys are discarded. Acquisition stays null; area/depth/exposure metrics are excluded.
- `FloodPublisher` stores one envelope per A/B slot in `satellite_flood_latest`: **two documents maximum, each at most 2 MiB**. Empty is valid. Invalid/incomplete candidates retain the last good generation. Existing writer locks, verified rollback, unique indexes and retention checks apply. `mongo_admin verify` covers the new product.
- The server reader uses bounded active-slot/run retries and fails unavailable on database/contract errors, with no production local fallback. Query freshness is separate from unknown acquisition age.
- API queries accept only known `area_id`. National/Central/Nakhon Nayok/Ongkharak views identify the pilot; other areas return OUT_OF_SCOPE, never no flood. Area summaries and source status use these same snapshots.
- A published envelope enables the checkbox even with zero records. The panel shows the pilot, query counts/times, unknown acquisition and empty-is-not-all-clear text, plus Open Ongkharak navigation. Forecast date changes do not alter source timestamps.
- Geometry uses flat blue-gray fill/outlines in 2D/3D, source tooltips and no metric extrusion. Delayed/failed query geometry is gray; TMD is a separate overlay. A valid empty snapshot counts as a connected source.

The new `Latest GISTDA Ongkharak flood product` workflow uses existing GISTDA/MongoDB secrets, contents:read, serialized publication, one bounded provider GET and database verification. Daily target: 09:27 ICT, with possible execution delay. Main-only reviewed requests select only the fixed operation, never endpoint/key/district/product. The initial request is added after the reader deploys.

## Verification

Local Python: **191 passed, 19 opt-in HTTP checks skipped**. Frontend: **19 tests**, TypeScript and production build passed. New tests cover empty/nonempty contracts, retention/rollback, partial candidate rejection, bounds/indexes, health recovery and request restrictions. The synthetic fixture is clearly marked offline QA and is never published as source data.

The real-engine harness was extended for the fourth product's publication/rollback/outage/restart but has not been rerun. The prior three-source real MongoDB report remains dated evidence. Real Atlas and browser results are recorded after the staged release; no synthetic data is sent to production.
