# Forecast background and overlay ordering

1 November 2026, Asia/Bangkok. This B increment makes the map background an explicit single choice: Off, daily Open-Meteo, or today's hourly Open-Meteo. Forecast metric and opacity controls are disabled while the fill is off; their selected values are retained. The forecast color legend disappears with the fill. Top-level Daily/Hourly buttons explicitly enable the selected forecast again.

Switching background, Situation/Daily/Hourly or 2D/3D preserves source overlay choices. HII observed rain remains a station point layer. Existing geography policy is retained: future dates support daily forecasts only; basin context has no accepted forecast fill, CAP or GISTDA basin product. Changing geography still applies those scope restrictions.

The two renderers share an explicit stack: forecast geography, existing rivers/place labels, GISTDA footprints, TMD CAP polygons, HII station points/clusters, then RID DOM markers. Owned native anchors place interleaved deck.gl layers consistently with the 3D native layers, including the minimal basemap fallback. Station hit routing and dam selection remain intact. No source data, thresholds, source clocks, geometry IDs or collection schedule changed.

Validation: 80 web unit tests, 267 Python tests, TypeScript check; browser checks with real public snapshot data confirm all five overlays and 35 dam markers survive Daily/Hourly/Off and 2D/3D, Off removes the forecast legend and retains the metric, and future-hourly/basin forecast options are disabled. Additional build, mobile and deployment results are recorded in the production receipt when verified. Local hourly product was unavailable, so that local check covers the controls and unavailable state, not real hourly values.

C0 findings are in [the radar source review](radar-source-review-2026-11-01.md). Radar/nowcasting is still unconnected; a reachable candidate page is not an accepted data contract.
