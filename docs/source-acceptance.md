# Current source acceptance

The project scope is Thailand. [Current scope](current-scope.md) supersedes local trial plans. National integration does not certify complete scientific coverage or fill absent observations.

| Source | Accepted current product | Limits |
| --- | --- | --- |
| Open-Meteo daily | 1,005 national representative-point forecasts, four daily periods | Forecasts are not measured area averages; issue time not supplied |
| Open-Meteo hourly | Separate 1,005-point Today forecast with 24 explicit Bangkok-day intervals | Preceding-hour rain; temperature at interval end; full validated generation only |
| RID | 35 daily large-dam storage reports | Report date is known; exact observation instant is not supplied |
| TMD | Public Actual CAP feed, original validity and geometry | Source time conflicts are flagged; missing, expired, superseded or cancelled messages never imply current warnings |
| GISTDA | Complete bounded retrospective 3days Thailand query, chunked storage | Acquisition unknown; administrative membership does not imply polygon clipping, depth or full satellite coverage |
| HII / ThaiWater | National station endpoint discovery only | Timezone, station quality, integration quota and live-product republication scope still unresolved; gauge layer unavailable |

Keep each agency's attribution and semantics. Country scope means collecting the accepted unfiltered response and supporting all canonical areas, not asserting every province has a valid observation. Do not restrict source ingestion to an example district or a small local station list.

Current GISTDA behavior is specified in [the three-day release](gistda-three-day-release-2026-10-29.md); current HII evidence is in [the national review](thaiwater-access-review-2026-10-29.md). Prior discovery and local trial records are archived and are not operating instructions or persistent user preferences.
