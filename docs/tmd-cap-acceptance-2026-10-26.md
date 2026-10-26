# TMD public CAP acceptance — 26 October 2026

Accepted product: `tmd:cap_warnings`, the latest public CAP/RSS messages from the Thai Meteorological Department. Registered forecast, radar, earthquake and other TMD products are separate and remain unaccepted.

## Source, access and permission

- TMD's public open-RSS directory explicitly links **เตือนภัย CAP**: https://www.tmd.go.th/service/rss . The linked feed is https://www.tmd.go.th/api/xml/CAP . A direct request returned RSS 2.0 with six uniquely identified document links and channel copyright `public domain`.
- The [WMO Register of Alerting Authorities](https://alertingauthority.wmo.int/authorities.php?recId=164) identifies TMD and the same Thai/English CAP feed URLs. The implementation consumes the Thai feed only, over HTTPS with normal certificate verification; it does not claim digital-signature verification.
- TMD's [copyright notice](https://www.tmd.go.th/content/copyright) permits public non-commercial republication with TMD attribution. The user already confirmed personal/non-commercial public use. The feed declaration and this more conservative website condition are both retained; commercial use is outside this implementation's accepted scope.
- The [website policy](https://www.tmd.go.th/content/policy) identifies provider-prepared channels as the allowed route for automation. This implementation consumes the explicitly published RSS and its CAP documents. It does not scrape dashboards, register an account, accept new account terms, borrow keys, reproduce logos or imply TMD endorsement.
- No numeric quota was found in the reviewed RSS documentation. One hourly feed request plus sequential linked-document requests, one-second document pacing and at most four bounded attempts per request are the chosen conservative policy, not a provider quota guarantee. More than 50 items, 4 MiB of combined fetched bodies or a collection exceeding the bounded time budget fail the run without truncating/promoting an incomplete feed.

## Actual product evidence

The 26 October feed contained six Actual/Public CAP 1.2 messages, all with expiry instants before retrieval. The latest two were issued on 25 October and expired at 18:00 ICT that day. Three older messages were superseded by explicit updates. All six were expired by time; lifecycle labels prioritize cancellation/supersession where applicable. A newly assembled/retrieved RSS feed is not a newly issued warning, an all-clear statement or proof of national completeness.

All 481 published polygon rings passed closure, finite WGS84 coordinate and polygon-topology checks. All explicit ISO3166-2 province codes matched canonical province IDs. The first message's geocodes contain TH-38 while its prose omits that province name; both source statements are retained, rather than silently rewriting the source. District-specific applicability is not inferred from a province reference.

CAP's `sent` is authoritative for message issuance. In the captured feed, RSS item `pubDate` and CAP `sent` have a seven-hour discrepancy; the adapter never substitutes the RSS item date. Feed `lastBuildDate` is assembly metadata, stored separately. Source geometry is converted from CAP latitude,longitude to GeoJSON longitude,latitude without simplification, interpolation or topology repair.

## Message semantics and bounded storage

The [OASIS CAP 1.2 specification](https://docs.oasis-open.org/emergency/cap/v1.2/CAP-v1.2-os.html) defines messages, references, effective/expiry instants and WGS84 polygons. This adapter:

- Accepts Actual/Public Alert, Update and Cancel messages from sender TMD. Test/non-public entries are excluded and counted. Unsupported public message types fail closed.
- Preserves agency severity, urgency, certainty, original headline, description and instructions as plain text. No project-generated severity or flood-risk class is assigned.
- Applies exact sender/identifier/sent references to supersession and cancellation. Missing expiry remains unknown. Missing `effective` uses CAP's specified `sent` default and records that provenance.
- Selects one Thai information block, or the sole information block when unambiguous. Multiple ambiguous blocks, new circle geometry or unknown province codes require separate review and fail closed.
- Rejects oversized XML, DTD/entities, alternate-encoding entity bypasses, external/redirected document URLs, invalid identity, geometry and time intervals. Document links must come from the official feed and remain under the accepted HTTPS CAP path.

`agency_warning_latest` holds two bounded feed envelopes, not an append-only warning archive. Each envelope has at most 50 messages and must remain below 2 MiB in both BSON and compact UTF-8 JSON, keeping responses below platform response limits. One envelope can explicitly contain an empty successfully fetched feed; that is distinct from an unavailable source. Control/status/lock key `tmd:cap_warnings` is independent of weather and RID. A candidate is promoted only after all linked items are fetched, validated or explicitly counted as non-public/test exclusions.

Completeness 1.0 means complete processing of the listed feed items; it does not mean complete geographic or agency-product coverage. Public `message_states` and `current_count` are computed against the whole stored feed, including references outside an area-filtered response.

## Display and refresh

Hourly GitHub Actions ingestion is independent of website requests. The browser rereads the stored snapshot every five minutes; the server/CDN also caches reads. Scheduler and cache delay mean this is a periodically collected snapshot, not a live warning-delivery service.

Feed freshness uses the older of retrieval and feed assembly: up to two hours FRESH, up to six DELAYED, then STALE. Failed refresh downgrades a fresh old feed to DELAYED. Message validity separately uses CAP effective/expiry and references. Current thematic outlines appear only for messages within their validity window from a FRESH feed. Delayed/stale data pauses those colors. Explicitly selected expired/superseded/cancelled/unknown messages use gray reference outlines and a non-current caption. No expiry is extended by retrieval, date selection or deployment.

The initial real capture correctly shows **zero messages within validity and six previous feed messages**. This is not presented as safe conditions or absence of every official warning. Forecast timeline changes leave CAP dates unchanged. Attribution and source links appear in the message panel, registry and methodology.

## Verification

Real public captures are preserved under `tests/fixtures/tmd/` with attribution. Automated tests cover parsing, timezone conversion, all polygon rings, province geocodes, null expiry, CAP defaults, update/cancel references, rejected unsafe XML/URLs, partial retrieval, bounded slots, empty feeds and rollback. Browser checks use real captured messages; synthetic current/cancel cases exist only in isolated tests. See `execution-status.md` for publication and end-to-end evidence.
