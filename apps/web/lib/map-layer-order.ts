import type {Map as MapType} from 'maplibre-gl';

// Owned native anchors also work with the minimal fallback basemap.
export const mapLayerAnchors={forecast:'weather-background-end',flood:'warning-cap-fill',cap:'gauge-clusters'} as const;
export function orderMapLayers(map:Pick<MapType,'getStyle'|'moveLayer'>,baseIds:ReadonlySet<string>){
  const layers=map.getStyle().layers;
  const foreground=layers.filter(layer=>baseIds.has(layer.id)&&
    (layer.type==='symbol'||(layer.type==='line'&&'source-layer' in layer&&layer['source-layer']==='waterway')));
  for(const id of ['weather-native-fill','weather-native-line','weather-native-extrusion',mapLayerAnchors.forecast,'radar-image-layer',
    ...foreground.filter(layer=>layer.type==='line').map(layer=>layer.id),
    ...foreground.filter(layer=>layer.type==='symbol').map(layer=>layer.id)]){
    map.moveLayer(id,'gistda-flood-fill');
  }
}
