# Current source acceptance

The project scope is Thailand. [Current scope](current-scope.md) supersedes local trial plans. National integration does not certify complete scientific coverage or fill absent observations.

| Source | Accepted current product | Limits |
| --- | --- | --- |
| Open-Meteo daily | 1,005 national representative-point forecasts, four daily periods | Forecasts are not measured area averages; issue time not supplied |
| Open-Meteo hourly | Separate 1,005-point Today forecast with 24 explicit Bangkok-day intervals | Preceding-hour rain; temperature at interval end; full validated generation only |
| RID | 35 daily large-dam storage reports | Report date is known; exact observation instant is not supplied |
| TMD | Public Actual CAP feed, original validity and geometry | Source time conflicts are flagged; missing, expired, superseded or cancelled messages never imply current warnings |
| TMD radar composite | Qualified original rain-rate image display; separate from CAP | UTC frame time, provider placement and mm/hour source scale; transparent/no-echo/missing coverage ambiguous; no pixel values or accumulated QPE. [Acceptance](tmd-radar-acceptance-2026-11-04.md) |
| GISTDA | Complete bounded retrospective 3days Thailand query, chunked storage | Acquisition unknown; administrative membership does not imply polygon clipping, depth or full satellite coverage |
| HII / ThaiWater water level | Connected unfiltered national automatic station response and selected-station history | Original wall time, unknown observation UTC/age, distinct meter/MSL values; no flood depth or accepted danger thresholds; unrestricted licensing/quota/SLA not established |
| HII / ThaiWater rain | Independent connected national rain_24h product with reported mm/24h and mm/1h | Original wall time and unknown UTC accumulation bounds; station values are not area means; zero differs from missing; unrestricted licensing/quota/SLA not established |
| DDPM 22 basins | Connected simplified boundary context with conservative HII/RID point matching | Near-border points remain unmatched; no inferred river network or unsupported basin forecasts/warnings; unrestricted licence not established |

Keep each agency's attribution and semantics. Country scope means collecting the accepted unfiltered response and supporting all canonical areas, not asserting every province has a valid observation. Do not restrict source ingestion to an example district or a small local station list.

Current GISTDA behavior is specified in [the three-day release](gistda-three-day-release-2026-10-29.md). Current HII evidence is in [the national water-level release](hii-national-release-2026-10-30.md) and [rain/province/basin release](province-rain-basin-release-2026-10-30.md). The earlier [access review](thaiwater-access-review-2026-10-29.md) records discovery, not current connection status. Prior discovery and local trial records are not operating instructions or persistent user preferences.

The connected eight products remain independent. Data receipt, deployment success, provider observation age and retrieval freshness are separate facts. A complete previous-day hourly generation is not a current Today forecast. Qualified TMD radar images are implemented separately; numerical QPE and nowcasting remain unconnected pending source-specific acceptance.

The [1 November radar/QPE/nowcasting review](radar-source-review-2026-11-01.md) records reachable replacement composite links and unresolved product semantics, time/coverage and reuse terms. It accepts no new production product.

The [4 November qualified image acceptance](tmd-radar-acceptance-2026-11-04.md) supersedes the earlier no-acceptance decision for TMD composite PNG display only. See [the image player release](radar-release-2026-11-04.md).
