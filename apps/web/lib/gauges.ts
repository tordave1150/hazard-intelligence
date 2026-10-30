import type {Area,GaugeStation,GaugeSnapshot,Freshness} from './types';

export const gaugeName=(row:Pick<GaugeStation,'name_th'|'name_en'|'station_code'|'gauge_id'>)=>row.name_th??row.name_en??row.station_code??row.gauge_id;
export const gaugeInArea=(row:Pick<GaugeStation,'province_id'|'district_id'|'region_id'|'basin_id'>,area:Area)=>area.level==='basin'?row.basin_id===area.id:area.level==='national'||row.province_id===area.id||row.district_id===area.id||row.region_id===area.id;
export const gaugeValue=(value:number|null)=>value===null?'ไม่ระบุ':value.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:3});
export const gaugeWallTime=(value:string|null)=>value?`${value} · เวลาต้นทาง ไม่ระบุเขตเวลา`:'ไม่ระบุเวลาตรวจวัด';
export function gaugeQueryFreshness(feed:{fetched_at:string}|null,now=Date.now(),failed=false):Freshness{
  if(!feed)return 'UNAVAILABLE';
  const stamp=Date.parse(feed.fetched_at);
  if(!Number.isFinite(stamp)||stamp>now+300000)return 'UNKNOWN';
  const hours=(now-stamp)/3600000;
  return hours<=4&&!failed?'FRESH':hours<=8?'DELAYED':'STALE';
}
export function gaugeResponse(snapshot:GaugeSnapshot,area:Area){
  const records=snapshot.records.filter(row=>gaugeInArea(row,area));
  return {...snapshot,records,source_id:'thaiwater',integration_status:'national_query',scope_area_id:'TH',selected_area_id:area.id,
    total_count:snapshot.feed?.record_count??null,selected_count:snapshot.feed?records.length:null,
    status:!snapshot.feed?'UNAVAILABLE':records.length?'AVAILABLE':'EMPTY_RESULT',
    coverage:snapshot.feed?.coverage??'No published station response',observation_time_status:'TIMEZONE_NOT_SUPPLIED'};
}
