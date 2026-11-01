import type {Map as MapType,ExpressionSpecification} from 'maplibre-gl';
import type {Feature,MultiPolygon,Polygon} from 'geojson';
export type CountryFocus=Feature<Polygon|MultiPolygon>;
export type TimeTheme='dawn'|'day'|'dusk'|'night';
export function timeTheme(now:number):TimeTheme{
  const parts=new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Bangkok',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(now);
  const minutes=Number(parts.find(p=>p.type==='hour')!.value)*60+Number(parts.find(p=>p.type==='minute')!.value);
  return minutes<300||minutes>=1110?'night':minutes<420?'dawn':minutes<1020?'day':'dusk';
}
export const mapPalettes={
  dawn:{land:'#f4e7d5',water:'#abc6ca',park:'#d7ddc1',building:'#dfcdbb',road:'#fff4df',boundary:'#aa9387',text:'#494744',halo:'#f4e7d5',river:'#568c9d',focus:'#688775',outside:'#9e948b'},
  day:{land:'#f1f4ed',water:'#b8d9e4',park:'#d2e4ce',building:'#dce0d7',road:'#ffffff',boundary:'#a4b2ac',text:'#3e5354',halo:'#f5f7f1',river:'#467f9a',focus:'#527e74',outside:'#8b9e9e'},
  dusk:{land:'#383b55',water:'#252f50',park:'#414b59',building:'#505069',road:'#62647c',boundary:'#88829d',text:'#eee4f1',halo:'#34364d',river:'#80b6d0',focus:'#a0c9bd',outside:'#11182c'},
  night:{land:'#172333',water:'#101b2d',park:'#20343c',building:'#28394b',road:'#46566b',boundary:'#687a91',text:'#d7e3f0',halo:'#152232',river:'#76abc3',focus:'#86bcaf',outside:'#030b17'}
} satisfies Record<TimeTheme,Record<string,string>>;
export const contextShadeOpacity:Record<TimeTheme,number>={dawn:.24,day:.28,dusk:.48,night:.52};
export const riverLineWidth:ExpressionSpecification=['interpolate',['linear'],['zoom'],
  3,['case',['==',['get','class'],'river'],1.1,0],
  6,['case',['==',['get','class'],'river'],1.8,0],
  10,['case',['==',['get','class'],'river'],2.3,.7],14,3];
export function placeLabelOpacity(country:CountryFocus):ExpressionSpecification{
  return ['interpolate',['linear'],['zoom'],3,['case',['within',country],1,.16],
    8,['case',['within',country],1,.45],10,1];
}
export function applyTimeTheme(instance:Pick<MapType,'getStyle'|'setPaintProperty'>,baseIds:ReadonlySet<string>,theme:TimeTheme,country?:CountryFocus){
  const layers=instance.getStyle()?.layers;if(!layers)return;
  const palette=mapPalettes[theme];
  for(const layer of layers){
    if(!baseIds.has(layer.id))continue;
    const sourceLayer='source-layer' in layer?String(layer['source-layer']):'';
    if(layer.type==='background')instance.setPaintProperty(layer.id,'background-color',palette.land);
    if(layer.type==='fill')instance.setPaintProperty(layer.id,'fill-color',sourceLayer.includes('water')?palette.water:sourceLayer==='building'?palette.building:['park','landcover','landuse'].includes(sourceLayer)?palette.park:palette.land);
    if(layer.type==='line'){
      instance.setPaintProperty(layer.id,'line-color',sourceLayer==='waterway'?palette.river:sourceLayer.includes('water')?palette.water:sourceLayer==='boundary'?palette.boundary:palette.road);
      if(sourceLayer==='waterway'){
        instance.setPaintProperty(layer.id,'line-width',riverLineWidth);
        instance.setPaintProperty(layer.id,'line-opacity',.88);
      }
      if(sourceLayer==='transportation')instance.setPaintProperty(layer.id,'line-opacity',['interpolate',['linear'],['zoom'],3,.25,7,.55,12,1]);
    }
    if(layer.type==='symbol'&&layer.layout?.['text-field']){
      instance.setPaintProperty(layer.id,'text-color',sourceLayer==='waterway'?palette.river:palette.text);
      instance.setPaintProperty(layer.id,'text-halo-color',palette.halo);
      if(sourceLayer==='place'&&country){
        const opacity=placeLabelOpacity(country);
        instance.setPaintProperty(layer.id,'text-opacity',opacity);
        if(layer.layout['icon-image'])instance.setPaintProperty(layer.id,'icon-opacity',opacity);
      }
      if(sourceLayer==='transportation_name')instance.setPaintProperty(layer.id,'text-opacity',['interpolate',['linear'],['zoom'],3,.2,8,.5,12,1]);
    }
  }
}
