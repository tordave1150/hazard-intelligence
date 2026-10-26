# GISTDA product #25 — access inspection in progress

The user reports obtaining a credential for **ข้อมูลขอบเขตพื้นที่น้ำท่วม (1 วันย้อนหลัง)** and supplied this exact endpoint, without a key:

`https://api-gateway.gistda.or.th/api/2.0/resources/gi-service/v1.1/disasters/flood-extent-1day`

## Observed evidence

- One direct GET without credentials returned **HTTP 407**, JSON `{"status":407,"detail":"Authentication Required"}`. This confirms the public URL requires authentication; it does not validate the user's credential or product entitlement.
- The supplied cropped image includes `area=undefined`, but the complete request/error cannot be read. Required area syntax, coverage and the response geometry/time fields remain unknown.
- The indexed official [flood-extent catalog](https://opendata.gistda.or.th/th/dataset/disasters-03) describes a distinct product from the previously reviewed Disaster Platform catalog. Its indexed metadata lists Open Data Common, point/geometry resources, Postman documentation and a v1.0 URL with `api_key`. Direct access now redirects to catalog login; a public CKAN package read returned 403. The current full terms/documentation could not be inspected. Do not transfer the unspecified license of the separate Disaster Platform dataset to this product, or declare the current product license accepted from a search excerpt alone.
- No borrowed, published example or other application's key was used. No real credential was read from chat, local configuration or GitHub.

## Prepared manual diagnostic

`.github/workflows/gistda-access.yml` is **Inspect GISTDA flood API response**. It makes one bounded HTTPS GET to the exact selected v1.1 endpoint, with repository secret `GISTDA_API_KEY`. The `api_key` query convention comes from the indexed official catalog; its actual v1.1 compatibility is being tested. Optional `area` is included only when the user supplies a documented value. Blank area is omitted; `undefined`, `null`, key-containing values and pasted credential URLs are rejected.

The diagnostic does not connect to MongoDB, write snapshots, publish geometry, follow redirects, retry requests or run on a schedule. The response is capped at 2 MiB and inspected as UTF-8 JSON. Logs expose bounded identifier-like field names/types and counts only, with no values, reflected URL, credentials, response headers or exceptions. Transport failures and HTTP/provider errors have fixed reason codes. A 2xx response still reports **SCHEMA_UNVERIFIED**; it is not a source-acceptance result.

Six isolated tests cover secret/URL reflection, the exact single-request target, omitted versus explicitly supplied area, auth/redirect/provider error handling, exception sanitization and input/response bounds. No real key is involved in those tests.

## Still needed before integration

1. Repository secret configuration and the first manual diagnostic result.
2. Current #25 documentation: authentication, required area syntax, query coverage, quota and permitted redistribution/attribution.
3. Real accepted sample: geometry or layer reference, acquisition time/precision, publication versus retrieval time, missing/empty response semantics, units/CRS and product quality.
4. A bounded source-specific publisher/reader and tests appropriate to the actual product, followed by map/API verification.

The `1 day` product name alone does not identify a satellite acquisition instant, a complete national mosaic, or present floodwater conditions. No timestamp, coordinate, valid empty result, map extent or risk value is inferred from it. The production layer remains planned/unavailable while these concrete inputs are missing.

## Parameter and credential follow-up

The user's later example confirms query names `lat`, `lon`, `area`; all three values are `undefined`, so the area syntax/units are still unverified. The diagnostic now accepts a validated finite latitude/longitude pair. Its manual form defaults to the existing public project Bangkok representative point, (13.719961, 100.602017), as a query location only. It is not a station coordinate or asserted flood location. No `area` is supplied unless explicitly entered from documentation. Clearing both coordinates remains an authentication-only check; a partial pair or undefined/non-finite/out-of-range values fail before network access. Single-point results cannot establish nationwide coverage.

The user inadvertently included a real credential in a link. It was not copied to code, logs, files or an API request. The user was instructed to revoke it, issue a replacement and update the existing repository secret; credentialed testing is pending that update. A redacted endpoint is sufficient for documentation and the raw submitted link is not retained in this repository. The diagnostic's eight tests now also cover coordinate encoding and invalid pair rejection.

## First workflow result and documented version discrepancy

The user confirmed replacing the credential and updating the secret, then started run [40340511359](https://github.com/tordave1150/hazard-intelligence/actions/runs/40340511359) on `e91ede62b3309c1cc4aee3b3f2e3041d059d899e`. Job 121633628351 completed setup and the HTTP request, but the provider returned **HTTP 404**, with object fields `message:string`, `error:string`, `statusCode:number`. The tested request used the v1.1 endpoint, paired coordinates and omitted unknown area. No response values or key were logged; no data was accepted or published. This differs from the unauthenticated 407 response but does not itself prove full credential entitlement, absence of floods, or the reason for the 404.

The live [DGA catalog](https://data.go.th/dataset/disasters-03) was then read successfully (HTTP 200, saved ignored HTML). It identifies the same one-day point/geometry product, **Open Data Common**, and a **v1.0** point URL using latitude/longitude and api_key. This is direct official metadata, not only a search excerpt. Its resource links [GISTDA's published Postman collection](https://documenter.getpostman.com/view/21652831/2sBXcKCyhC#03600e7f-3ee4-4d24-b510-48312a8326f1); the current collection rendered disaster recurrence/burnt-area products rather than the one-day endpoint at that anchor. Flood recurrence is explicitly a multi-year frequency product, so its measurements and example geometry were not adopted for the one-day layer.

The manual form now allows only the two specifically observed endpoint versions, defaulting to catalogued **v1.0** for the next diagnostic. Exactly one selected endpoint is requested per run; no automatic alternate-version fallback or endpoint search occurs. New fixed error hints can identify a framework `Cannot GET/POST` signal or which of the three known parameters appears literally undefined, without disclosing the upstream URL or any response text/credential. Ten tests cover this extended diagnostic, including version allowlisting and reflected upstream error sanitization. The next real response is still pending; source acceptance and the production layer remain incomplete.

## v1.0 result — both published versions return 404

The user's fresh run [40343281341](https://github.com/tordave1150/hazard-intelligence/actions/runs/40343281341) on `5fbdb4bdd9a85d54942d03d9eddd4f69ebdba339`, job 121643400048, completed checkout/setup and the selected v1.0 point request. It returned **HTTP 404** with object fields `status:number`, `detail:string`; the diagnostic failed rather than publishing an accepted empty observation. Area remained omitted and the paired point was supplied. Its workflow window was 26 October 2026 14:49:37–14:49:56 UTC / 21:49:37–21:49:56 ICT. These are workflow times, not satellite times or exact request timestamps.

No valid daily flood sample has been obtained from either specifically published version. The different error structures do not establish full key entitlement, the precise failing upstream route, required area semantics, or safe/no-flood conditions. No blind retries, further credential rotation, alternate credentials, guessed area geometry or recurrence substitution are proposed from this evidence alone. Current product URL/method/parameter and entitlement confirmation from GISTDA is the concrete next dependency.

A [Thai support-request draft](GISTDA_PRODUCT25_SUPPORT_REQUEST_TH.md) includes both credential-free request descriptions, run references, times and questions for the official catalog contact. It has not been sent. The source registry now identifies this selected product and the actual 404 limitation, rather than saying no credential is configured or applying the different Disaster Platform dataset's unspecified license to #25. Production still returns unavailable; no data write, raster storage or layer activation occurred. CI run 40342505814 passed the diagnostic code and Vercel deployed it successfully before this result record.

## User-requested Ongkharak point experiment

The user proposed Ongkharak because they report flooding there. The next manual probe defaults to **14.097076, 101.010122**, the unchanged representative interior point of canonical **TH-D-2604 / องครักษ์**, Nakhon Nayok province TH-P-26. Its containment is checked against the project's pinned district geometry. The user's report motivates the query; it is not an independently accepted flood observation, a station location or a guarantee that this particular point is wet or covered by the satellite product.

The version default returns to portal v1.1 so that a new point can be compared with the earlier v1.1 Bangkok request. It still makes exactly one selected-version GET, leaves unverified area omitted and writes no database data. The two historical Bangkok request coordinates/results in the support draft remain unchanged. This is a newly requested point experiment rather than automatic repetition of the same failed request. Its provider result remains pending a fresh Run workflow on main; the selected source is still unavailable until an actual response passes acceptance.
