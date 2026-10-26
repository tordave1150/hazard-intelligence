# Unified map design

The operational route is `/`. Source registry and methodology are supporting routes, not separate operational dashboards.

- Administrative navigation: Thailand → six pinned upstream reg_royin regions → province → district; breadcrumbs and Back to Thailand preserve metric, layer opacity and 2D/3D selection. Search accepts English names, Thai names and canonical IDs.
- National map uses simplified province geometry and point forecasts. Selecting a national polygon first chooses its region; within a region it chooses a province. Province/district views lazily load only the selected province's district file. Raw boundaries remain in `data/boundaries/raw`.
- deck.gl GeoJsonLayer handles 2D fill, selection and tooltips. MapLibre native fill, line and fill-extrusion layers handle 3D so geometry participates in DEM terrain rendering instead of sinking below it. Camera changes combine area bounds and pitch in one operation to prevent competing transitions.
- MapLibre terrain uses Mapterhorn raster-dem tiles with 1.2× visual exaggeration. Basemap uses OpenFreeMap Positron, with automatic service attribution. A basemap loading failure falls back to a local background plus static polygons; WebGL loss is disclosed while area controls remain usable.
- Rainfall display breaks: 0, 1, 10, 25, 50+ mm/24h. Probability breaks: 0, 20, 40, 60, 80+ percent. These are display scales, not validated danger thresholds. Missing/stale values are neutral gray.
- Local extrusion: rainfall ×150 display meters or probability ×50 display meters. The legend and controls explain that height has no flood-depth meaning. Extrusion requires local view, selected weather layer and a non-stale metric.
- Timeline contains only actual available daily forecast dates. It is not historical or satellite replay. Every weather panel discloses validity, source, requested/returned grid coordinates and retrieval time; model issue time remains explicitly unavailable.
- Desktop uses left controls, center map, right area evidence. At ≤900px, panels become overlay drawers with close buttons and map remains central. Modal source details support Escape and keyboard focus cycling. Reduced-motion CSS is included; device GPU/memory benchmarking remains a release task.

Gauge/dam/radar/warning/satellite layers remain planned and disabled until their source acceptance gates pass. Basin mode is disabled until authoritative licensed geometry and area intersections exist. These states do not imply normal weather or absence of warnings.
