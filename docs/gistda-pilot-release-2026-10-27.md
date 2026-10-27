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

## Observed release results

Reader commit **66231dd** passed CI 40542301093 and Vercel before the first publication request. Writer request commit **07eb9f8** started [run 40542746005](https://github.com/tordave1150/hazard-intelligence/actions/runs/40542746005), job 122325168278. Every step passed, including verification before/after publication. The real source response was **2026-10-27T16:38:07.775Z / 23:38:07.775 ICT**, retrieval 16:38:07.933745Z, successful publication 16:38:10.859901Z. The provider returned **zero features** and a complete district query. Acquisition remains null. No synthetic fixture or 30-day replacement was published.

Atlas verification: weather 1,005 active / 2,010 stored (bound 2,010); RID 35 / 70 (bound 70); TMD one envelope / two stored (bound two); GISTDA **one envelope / one stored (bound two), containing zero features**. All required unique indexes passed. A value-free receipt is saved at `artifacts/gistda-connected-release-2026-10-27.json`.

The production API returned EMPTY_RESULT, storage=mongo, query_freshness=FRESH, observation_freshness=UNKNOWN and health SUCCESS. Area filtering returned OUT_OF_SCOPE for Mae Sai, preserving its distinction from a genuine empty Ongkharak query. The 19 production HTTP checks passed; JUnit: `artifacts/gistda-connected-http-2026-10-27.xml`.

Source-panel interaction commit **35a0f81** passed CI 40543983105 and Vercel. The last selected source moves to the top while all checked overlays remain visible. Production browser checks verified TMD orange boundaries and both enabled checkboxes together, the real GISTDA empty panel, Open Ongkharak navigation, outside-pilot messaging, independent forecast/satellite times and mobile drawer activation. Mobile document client/scroll widths were both 375px at a 390x844 viewport. No warning/error console entries were observed. Screenshots: `artifacts/warnings-restored-production-2026-10-27.png`, `artifacts/gistda-and-warnings-connected-production-2026-10-27.png`, `artifacts/gistda-connected-mobile-2026-10-27.png`.

Separate **owned loopback QA** exercised a clearly labelled synthetic nonempty footprint through the actual reader/API, 2D/3D map, selection panel and forecast-date independence. These QA screenshots/fixture were never published as observations. A production-mode server pointed to an unreachable loopback MongoDB returned UNAVAILABLE even while that local synthetic preview existed. The initial server-cleanup failure was resolved; all owned processes stopped, port 3002 was free, the temporary preview file was removed, browser viewport overrides were reset and test tabs closed. Evidence: `artifacts/gistda-local-qa/`. This is not a test of Atlas infrastructure failover or a rerun of the real-engine restart harness.

The final reader bound also matches the publisher's per-feature 256-ring limit; its regression, TypeScript and production build passed. Remaining limitations are explicit: pilot district only, 100-feature/2-MiB one-response cap, unknown acquisition/coverage and no area/depth/impact metrics. Physical-device/GPU testing, Vercel platform rollback access, HII and basin work remain separate roadmap tasks. The global all-work-complete shutdown condition is not met.
