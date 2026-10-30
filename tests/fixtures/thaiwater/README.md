# ThaiWater public station subset

Three unchanged automatic rows and one manual row sampled from the official, unfiltered public response fetched 2026-10-29 16:38:43 UTC:
https://api-v3.thaiwater.net/api/v1/thaiwater30/public/waterlevel_load

Attribution: HII / ThaiWater and original measuring agencies. Live-product republication terms are not represented as an unrestricted licence. The subset exercises two Thai provinces and one provider-labelled foreign province. It is test evidence, never a production fallback or station allowlist.

`normalized-subset.json` is generated from this subset. All observation UTC timestamps remain null because the source wall timestamps do not supply timezone. Retrieval time is independently recorded. MSL levels are not flood depth. Manual discharge values are not substituted for missing water levels.
