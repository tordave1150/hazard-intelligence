# ThaiWater current station discovery — 29 October 2026

One credential-free, bounded GET to the public endpoint used by [ThaiWater's own portal](https://www.thaiwater.net/) succeeded. The URL was observed in the portal's public application bundle, rather than inferred from the exchange-format documentation:

`https://api-v3.thaiwater.net/api/v1/thaiwater30/public/waterlevel_load`

The initial response had 804 automatic station rows with 804 unique station IDs and 35 separate manual rows. Integration covers all Thailand stations supplied by the unfiltered endpoint; there is no station allowlist.

A second unfiltered check at 23:12 ICT returned 805 automatic station IDs: 802 rows match canonical Thai province codes in 76 provinces, and 3 have provider country labels identifying Myanmar. Amnat Charoen (`TH-P-37`) had no automatic row in this response. This is observed response coverage, not a claim that the country has only this many stations. The count-only [national scope receipt](thaiwater-national-scope-2026-10-29.json) records all province counts and the absence of a station allowlist. Station counts can change between requests.

The count-only [receipt](thaiwater-access-receipt-2026-10-29.json) contains no credentials and is evidence of discovery, not an accepted observation product. Raw website JavaScript and station responses remain ignored review artifacts. No embedded website credentials were used or added to the project.

## Source limitations retained by the qualified display

- Original `waterlevel_datetime` strings have minute precision without an offset or timezone. The sample range was `2026-10-22 14:00` through `2026-10-29 22:20`. A source-wide latest timestamp must not make older stations appear fresh. Preserve the original string until its timezone is documented.
- `waterlevel_m` and `waterlevel_msl` are separate fields, sometimes null, with values represented as strings. The [official ThaiWater manual](https://www.thaiwater.net/uploads/contents/Thaiwater_manual%20guide_2021.pdf), printed page 22, defines the distinction between meters and meters above mean sea level. This supplies the general unit meaning; station datum, missing-value conventions and quality still need to be retained and checked. Do not infer water depth from a mean-sea-level elevation.
- Provider `situation_level`, bank elevations and threshold fields exist. Their quality and operational meanings have not been accepted. Do not create a project risk score, reuse colors or derive alerts from these fields yet.
- A public portal request succeeding does not supply a documented integration quota, stability commitment or republication terms. The older monthly archive catalog's non-commercial license is not assumed to govern this live endpoint.

## Accepted implementation — 30 October 2026

Fetch the unfiltered national response and retain every supplied record for validation and accounting. Do not restrict ingestion to a preferred district or a small example station list. Use recognized provider Thai administrative codes for national/province/district views. Keep records identified by the provider as another country outside Thai statistics, with original country labels preserved. Unrecognized codes must remain unassigned rather than being shortened or guessed.

Use a separate station-observation contract and bounded A/B snapshot, station-specific observation/retrieval ages and missing-quality states. Counts must describe the current complete provider response, rather than requiring an invented permanent inventory of 802 stations or 77 populated provinces. Province navigation should include all 77 provinces, with an explicit unavailable state where no accepted station record exists. Keep HII and other contributing agencies attributed separately.

Treat the 35 manual rows as a separate product candidate: the reviewed response supplies neither water-level values nor coordinate pairs for them. Do not count them as 35 additional usable water-level map points or substitute discharge for water level. Collect a documented history endpoint before offering a trend chart; do not infer a trend from one latest/previous pair without timestamps. The implementation uses one bounded public GET per two-hour cycle, without claiming a documented numeric quota. Selected-station history uses the fixed public portal graph endpoint and a bounded 15-minute cache.

The national station contract and map now support a qualified display of source-reported measurements with observation UTC null, unknown observation age and neutral markers. This does not certify measurement calibration or supply undocumented live-product licensing. See [the current implementation release](hii-national-release-2026-10-30.md) for publication and production evidence.
