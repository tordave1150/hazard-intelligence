# ThaiWater current station discovery — 29 October 2026

One credential-free, bounded GET to the public endpoint used by [ThaiWater's own portal](https://www.thaiwater.net/) succeeded. The URL was observed in the portal's public application bundle, rather than inferred from the exchange-format documentation:

`https://api-v3.thaiwater.net/api/v1/thaiwater30/public/waterlevel_load`

The response had 804 automatic station rows with 804 unique station IDs and 35 separate manual rows. There were 7 automatic stations with provider province code `26` (Nakhon Nayok), including one with district code `04` (Ongkharak). The latter has station ID `189`, original station code `NYK000`. This makes a small Ongkharak/Nakhon Nayok pilot technically plausible. It does not establish the complete station inventory or national coverage.

The count-only [receipt](thaiwater-access-receipt-2026-10-29.json) contains no credentials and is evidence of discovery, not an accepted observation product. Raw website JavaScript and station responses remain ignored review artifacts. No embedded website credentials were used or added to the project.

## What still prevents a trustworthy current layer

- Original `waterlevel_datetime` strings have minute precision without an offset or timezone. The sample range was `2026-10-22 14:00` through `2026-10-29 22:20`. A source-wide latest timestamp must not make older stations appear fresh. Preserve the original string until its timezone is documented.
- `waterlevel_m` and `waterlevel_msl` are separate fields, sometimes null, with values represented as strings. Confirm station datum, missing-value conventions and the applicable units before numerical normalization or cross-station comparisons. Do not infer water depth from a mean-sea-level elevation.
- Provider `situation_level`, bank elevations and threshold fields exist. Their quality and operational meanings have not been accepted. Do not create a project risk score, reuse colors or derive alerts from these fields yet.
- A public portal request succeeding does not supply a documented integration quota, stability commitment or republication terms. The older monthly archive catalog's non-commercial license is not assumed to govern this live endpoint.

## Concrete next implementation once these facts are established

Start with the 7 pinned Nakhon Nayok station IDs from the receipt, keeping the one Ongkharak station identifiable. Use a separate station-observation contract and bounded A/B snapshot, station-specific observation/retrieval ages and missing-quality states. Keep HII and other contributing agencies attributed separately. Collect a documented history endpoint before offering a trend chart; do not infer a trend from one latest/previous pair without timestamps. Run one small refresh cycle under a documented quota before scheduling the source.

The source registry now records the discovered endpoint and the remaining acceptance gaps. `/api/gauges` and the map layer remain unavailable because no validated current observation product has been published.
