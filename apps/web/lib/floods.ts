import type {Area,Freshness,FloodFeed,FloodSnapshot} from './types';
import {areaById} from './geography';
import {contains} from './semantics';

export const floodScopeId='TH-D-2604';
export const floodSourceUrl='https://api-gateway.gistda.or.th/api/2.0/resources/features/flood/1day';
export const floodInArea=(area:Area)=>contains(area,areaById.get(floodScopeId)!);
export function floodQueryFreshness(feed:Pick<FloodFeed,'response_at'|'fetched_at'>|null,now=Date.now(),failed=false):Freshness{
  if(!feed)return 'UNAVAILABLE';
  const times=[Date.parse(feed.response_at),Date.parse(feed.fetched_at)];
  if(times.some(t=>!Number.isFinite(t)||t>now+300000))return 'UNKNOWN';
  const hours=(now-Math.min(...times))/3600000;
  return hours<=30&&!failed?'FRESH':hours<=48?'DELAYED':'STALE';
}
export const floodColor=(freshness:Freshness)=>freshness==='FRESH'?'#586da5':'#7a8088';
export function floodResponse(snapshot:FloodSnapshot,area:Area){
  const inScope=floodInArea(area);
  return {...snapshot,records:inScope?snapshot.records:[],source_id:'gistda',integration_status:'pilot',
    scope_area_id:floodScopeId,in_scope:inScope,
    status:!snapshot.feed?'UNAVAILABLE':!inScope?'OUT_OF_SCOPE':snapshot.records.length?'AVAILABLE':'EMPTY_RESULT',
    observation_freshness:snapshot.freshness};
}
