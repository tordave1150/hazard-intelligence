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
