import type {FloodWindow} from './types';
import {validFloodBounds,viewportFeatureLimit,viewportByteLimit,type FloodBounds,type FloodViewport} from './flood-viewport';
export async function loadFloodViewport(signal:AbortSignal,options:{window:FloodWindow;areaId:string;generation:string;bbox:FloodBounds;fetchedAt:string;sourceCount:number},fetcher:typeof fetch=fetch):Promise<FloodViewport>{
  const params=new URLSearchParams({window:options.window,area_id:options.areaId,generation:options.generation,bbox:options.bbox.join(',')});
  const response=await fetcher('/api/flood-products/viewport?'+params,{cache:'no-store',signal});
  if(!response.ok)throw Error('Viewport unavailable');
  const value=await response.json() as FloodViewport;
  if(signal.aborted)throw Error('Viewport cancelled');
  if(value.generation!==options.generation||value.window!==options.window||value.area_id!==options.areaId||value.fetched_at!==options.fetchedAt||value.source_record_count!==options.sourceCount||
    !validFloodBounds(value.bbox)||JSON.stringify(value.bbox)!==JSON.stringify(options.bbox)||!Array.isArray(value.records)||value.records.length>viewportFeatureLimit||
    !['AVAILABLE','PARTIAL','EMPTY','ZOOM_REQUIRED','INDEX_UNAVAILABLE','GEOMETRY_UNAVAILABLE'].includes(value.status)||typeof value.complete!=='boolean'||
    value.matched_count!==null&&(!Number.isInteger(value.matched_count)||value.matched_count<value.records.length||value.matched_count>options.sourceCount))throw Error('Viewport contract mismatch');
  if(value.complete!==(value.status==='AVAILABLE'||value.status==='EMPTY')||value.complete&&value.matched_count!==value.records.length||
    value.status==='AVAILABLE'&&!value.records.length||value.status==='EMPTY'&&value.records.length||!['AVAILABLE','PARTIAL'].includes(value.status)&&value.records.length)throw Error('Invalid viewport completeness');
  if(new TextEncoder().encode(JSON.stringify(value.records)).length>viewportByteLimit)throw Error('Viewport byte limit');
  const ids=new Set<string>();
  for(const row of value.records){if(!row||ids.has(row.id)||!/^[a-f0-9]{64}$/.test(row.id)||row.type!=='Feature'||row.properties!==null||!['Polygon','MultiPolygon'].includes(row.geometry?.type))throw Error('Invalid viewport feature');ids.add(row.id);}
  return value;
}
