# Source registry

Current scope: Thailand, updated 1 November 2026 (Asia/Bangkok). Machine-readable registry: `apps/web/data/source-registry.json`, presented at `/sources`. `/health` reports actual current source status. Dated production receipts are evidence of a reviewed generation, not a guarantee of current freshness.

| Source | Connected product | Qualifications / evidence |
| --- | --- | --- |
| Open-Meteo daily | 1,005 representative points, four daily periods | Forecast, not measured area mean; model issue time unknown; API access terms separate from CC BY data attribution |
| Open-Meteo hourly | Independent Today product at 1,005 representative points | Complete validated generation; preceding-hour rain/probability; instant temperature at interval end; previous-day data is stale, not Today coverage |
| RID | 35 daily large-dam storage reports | Report date only; normal/maximum capacity distinct; percent of normal capacity may exceed 100%; flows not accepted. [Acceptance](rid-acceptance-2026-10-26.md) |
| TMD | Public Actual CAP feed | Preserve original validity, severity, cancellation references and geometry; invalid time intervals stay qualified. No messages is not an all-clear. [Acceptance](tmd-cap-acceptance-2026-10-26.md) |
| TMD radar composite | Qualified original rain-rate image display; separate from CAP | UTC frame time, provider placement and mm/hour source scale; transparent/no-echo/missing coverage ambiguous; no pixel values or accumulated QPE. [Acceptance](tmd-radar-acceptance-2026-11-04.md) |
| GISTDA | Complete bounded retrospective 3days Thailand query | Unknown acquisition time; administrative membership is not clipping or complete satellite coverage; no unverified area/depth/impact metrics. [Release](gistda-three-day-release-2026-10-29.md) |
| HII / ThaiWater water level | Unfiltered national automatic station response, selected-station history | Original wall time, unknown observation UTC/age; meter and MSL values separate; no accepted danger thresholds or unrestricted live-data licence/quota/SLA. [Release](hii-national-release-2026-10-30.md) |
| HII / ThaiWater rain | Independent national rain_24h product | Reported mm/24h and mm/1h; unknown UTC accumulation-window instants; zero differs from missing; station counts/values are not area averages. [Release](province-rain-basin-release-2026-10-30.md) |
| DDPM 22 basins | Separate conservative HII/RID point context | Near-border points can remain unmatched; no inferred river network; no unsupported basin weather/CAP/GISTDA aggregation; unrestricted licence not established. [Geometry receipt](basin-context-source-2026-10-30.json) |
| Administrative boundaries | Pinned attributed geometry and canonical directory | 77 provinces/928 districts; official directory reference 2023-09-01, reviewed 2026-10-26; later registry changes/legal geometry unverified |
| OpenFreeMap / Mapterhorn | Attributed basemap and terrain | Preserve provider/source attribution; service availability and source terms apply |

The eight connected data products are independent. Basin boundaries are context geometry, not an eighth observation product. Public station counts vary by provider response; national collection does not fabricate missing provinces, records or observations.

Numerical QPE, nowcasting and a separate river-network dataset remain candidates pending product-specific acceptance. Qualified TMD composite images are described in the 4 November acceptance. Historical monthly HII archive samples and old 1day GISTDA trials do not set current defaults.

See [current acceptance](source-acceptance.md), [current scope](current-scope.md) and [latest production receipt](province-rain-basin-production-2026-10-30.json). Preserve each agency's attribution and the limits stated in its dated acceptance record.

The [1 November radar/QPE/nowcasting review](radar-source-review-2026-11-01.md) records reachable replacement composite links and unresolved product semantics, time/coverage and reuse terms. It accepts no new production product.

The [4 November qualified image acceptance](tmd-radar-acceptance-2026-11-04.md) supersedes the earlier no-acceptance decision for TMD composite PNG display only. See [the image player release](radar-release-2026-11-04.md).
