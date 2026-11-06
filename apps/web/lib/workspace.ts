import type {MapBackground} from './map-layer-state';
export type InspectorId='area'|'forecast'|'tmd'|'gistda'|'rid'|'thaiwater'|'thaiwater_rain';
export const inspectorLabels:Record<InspectorId,string>={area:'Area',forecast:'Forecast',tmd:'CAP',gistda:'GISTDA',rid:'Dams',thaiwater:'Water',thaiwater_rain:'Rain'};
export function visibleInspector(requested:InspectorId,enabled:InspectorId[]):InspectorId{
  return requested==='area'||enabled.includes(requested)?requested:'area';
}
export function datePresentation(date:string,today:string,geography:'administrative'|'basin'){
  if(geography==='basin'&&date!==today)return null;
  return {selectedDate:date===today?null:date,todayMode:'situation' as const,showRadar:false,rainfall:date!==today,inspector:(date===today?'area':'forecast') as InspectorId};
}
export function workspaceBackgroundAvailable(background:MapBackground,date:string,today:string,geography:'administrative'|'basin'){
  return background==='off'||background==='radar'&&date===today||geography==='administrative'&&(background==='daily'||background==='hourly'&&date===today);
}
