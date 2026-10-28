import type {Area,Freshness,FloodFeed,FloodSnapshot} from './types';
import {areaById} from './geography';
import {contains} from './semantics';

export const floodScopeId='TH-D-2604';
export const floodSourceUrl='https://api-gateway.gistda.or.th/api/2.0/resources/features/flood/1day';
export const floodWindowLabel='Previous 1-day window · ย้อนหลัง 1 วัน';
export function floodRefreshFailure(health:FloodSnapshot['health']):string|null{
  if(health?.status!=='FAILED')return null;
  switch(health.error_summary){
    case 'NATIONAL_FEATURE_BUDGET_EXCEEDED':return 'Latest GISTDA refresh exceeded the supported number of flood footprints.';
    case 'RESPONSE_TOO_LARGE':
    case 'CANDIDATE_GEOMETRY_LIMIT':return 'Latest GISTDA refresh exceeded the supported map data size.';
    case 'DEADLINE_EXCEEDED':return 'Latest GISTDA refresh could not finish within the collection time limit.';
    case 'INCOMPLETE_QUERY_NOT_PUBLISHABLE':
    case 'PROVIDER_COUNT_CHANGED_DURING_PAGINATION':
    case 'DUPLICATE_OR_REPEATED_PROVIDER_FEATURE':return 'Latest GISTDA refresh could not confirm a complete, consistent result.';
    default:return 'Latest GISTDA refresh failed.';
  }
}
type FeedMetadata=Omit<FloodFeed,'records'>;
export const floodInArea=(area:Area,feed:FeedMetadata|null)=>!!feed&&(feed.area_id==='TH'?area.level!=='basin':contains(area,areaById.get(feed.area_id)!));
export const floodScopeLabel=(feed:FeedMetadata|null)=>!feed?'Awaiting product':feed.area_id==='TH'?'Thailand query':'Ongkharak pilot';
export function floodRecordsInArea(snapshot:Pick<FloodSnapshot,'feed'|'records'>,area:Area){
  if(!floodInArea(area,snapshot.feed))return [];
  if(snapshot.feed?.area_id!=='TH'||area.id==='TH')return snapshot.records;
  return snapshot.records.filter(row=>(row.area_ids??[]).some(id=>{
    const member=areaById.get(id);return member&&contains(area,member);
  }));
}
export function floodQueryFreshness(feed:Pick<FloodFeed,'response_at'|'fetched_at'>|null,now=Date.now(),failed=false):Freshness{
  if(!feed)return 'UNAVAILABLE';
  const times=[Date.parse(feed.response_at),Date.parse(feed.fetched_at)];
  if(times.some(t=>!Number.isFinite(t)||t>now+300000))return 'UNKNOWN';
  const hours=(now-Math.min(...times))/3600000;
  return hours<=30&&!failed?'FRESH':hours<=48?'DELAYED':'STALE';
}
export const floodColor=(freshness:Freshness)=>freshness==='FRESH'?'#586da5':'#7a8088';
export function floodResponse(snapshot:FloodSnapshot,area:Area){
  const inScope=floodInArea(area,snapshot.feed),records=floodRecordsInArea(snapshot,area);
  return {...snapshot,records,source_id:'gistda',integration_status:snapshot.feed?.area_id==='TH'?'national_query':'pilot',
    scope_area_id:snapshot.feed?.area_id??null,selected_area_id:area.id,in_scope:inScope,
    status:!snapshot.feed?'UNAVAILABLE':!inScope?'OUT_OF_SCOPE':records.length?'AVAILABLE':'EMPTY_RESULT',
    observation_freshness:snapshot.freshness};
}
