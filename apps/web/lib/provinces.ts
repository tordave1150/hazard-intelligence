import {areas} from './geography';
import {bangkokDate,freshness} from './semantics';
import {damFreshness} from './dams';
import {gaugeQueryFreshness} from './gauges';
import {warningState,warningFreshness} from './warnings';
import type {Snapshot,DamSnapshot,GaugeSnapshot,WarningSnapshot,Freshness,RainSnapshot} from './types';

export type ProvinceFloodCounts={available:boolean;counts:Record<string,number>;fetched_at:string|null;query_freshness:Freshness;generation:string|null};
export type ProvinceRow={area_id:string;name:string;name_th:string;region_id:string|null;
  forecast:{rainfall_mm:number|null;rain_probability_pct:number|null;valid_start:string;valid_end:string;fetched_at:string}|null;
  warnings:{current:number;upcoming:number;time_unknown:number}|null;
  gauges:{count:number;with_level:number;quality_issues:number}|null;
  rain:{count:number;with_24h:number;quality_issues:number}|null;dams:{count:number;report_date:string|null}|null;flood_features:number|null;data_gaps:string[]};
export type ProvinceOverview={checked_at:string;forecast_date:string;rows:ProvinceRow[];
  sources:Record<string,{available:boolean;freshness:Freshness;fetched_at:string|null;note:string}>};
export function buildProvinceOverview(weather:Snapshot,dams:DamSnapshot,gauges:GaugeSnapshot,warnings:WarningSnapshot,floods:ProvinceFloodCounts,rain:RainSnapshot,now=Date.now()):ProvinceOverview{
  const date=bangkokDate(now),forecastById=new Map(weather.records.map(r=>[r.location_id,r]));
  const rows=areas.filter(a=>a.level==='province').map(area=>{
    const record=forecastById.get(area.id),period=record?.valid_periods.find(p=>p.date===date);
    const stationRows=gauges.records.filter(r=>r.province_id===area.id),damRows=dams.records.filter(r=>r.province_id===area.id);
    const rainRows=rain.records.filter(r=>r.province_id===area.id);
    const messages=warnings.records.filter(r=>r.area_ids.includes(area.id)),states=messages.map(r=>warningState(r,warnings.records,now));
    const gaps:string[]=[];
    if(!period||period.rainfall_mm===null||period.rain_probability_pct===null)gaps.push('forecast');
    if(!gauges.feed||!stationRows.length||stationRows.some(r=>r.quality_flags.length))gaps.push('gauges');
    if(!rain.feed||!rainRows.length||rainRows.some(r=>r.quality_flags.length))gaps.push('rain');
    if(!warnings.feed||states.includes('TIME_UNKNOWN'))gaps.push('warnings');if(!dams.records.length)gaps.push('dams');if(!floods.available)gaps.push('satellite');
    return {area_id:area.id,name:area.name,name_th:area.name_th,region_id:area.region_id,
      forecast:period&&record?{rainfall_mm:period.rainfall_mm,rain_probability_pct:period.rain_probability_pct,valid_start:period.valid_start,valid_end:period.valid_end,fetched_at:record.fetched_at}:null,
      warnings:warnings.feed?{current:states.filter(s=>s==='CURRENT').length,upcoming:states.filter(s=>s==='UPCOMING').length,time_unknown:states.filter(s=>s==='TIME_UNKNOWN').length}:null,
      gauges:gauges.feed?{count:stationRows.length,with_level:stationRows.filter(r=>r.water_level_msl!==null||r.water_level_m!==null).length,quality_issues:stationRows.filter(r=>r.quality_flags.length).length}:null,
      rain:rain.feed?{count:rainRows.length,with_24h:rainRows.filter(r=>r.rain_24h_mm!==null).length,quality_issues:rainRows.filter(r=>r.quality_flags.length).length}:null,
      dams:dams.records.length?{count:damRows.length,report_date:damRows[0]?.report_date??null}:null,
      flood_features:floods.available?floods.counts[area.id]??0:null,data_gaps:gaps};
  });
  const oldest=weather.records.map(r=>r.fetched_at).sort()[0]??null;
  return {checked_at:new Date(now).toISOString(),forecast_date:date,rows,sources:{
    forecast:{available:weather.records.length>0,freshness:freshness(weather.records,now),fetched_at:oldest,note:'Open-Meteo · จุดตัวแทนจังหวัด · พยากรณ์วันนี้ mm/24h ไม่ใช่ฝนตรวจวัดหรือค่าเฉลี่ยทั้งจังหวัด'},
    warnings:{available:warnings.feed!==null,freshness:warningFreshness(warnings.feed,now,warnings.health?.status==='FAILED'),fetched_at:warnings.feed?.fetched_at??null,note:'TMD · จำนวนประกาศตามรหัสจังหวัดและช่วงเวลาที่มีผล; ไม่รวมรายการที่ยืนยันเวลาไม่ได้ในจำนวนปัจจุบัน'},
    gauges:{available:gauges.feed!==null,freshness:gaugeQueryFreshness(gauges.feed,now,gauges.health?.status==='FAILED'),fetched_at:gauges.feed?.fetched_at??null,note:'HII · ความสดของการดึงเท่านั้น; เวลาตรวจวัดไม่ระบุเขตเวลา จำนวนสถานีไม่ใช่ระดับความเสี่ยง'},
    rain:{available:rain.feed!==null,freshness:gaugeQueryFreshness(rain.feed,now,rain.health?.status==='FAILED'),fetched_at:rain.feed?.fetched_at??null,note:'HII · จำนวนสถานีฝนตรวจวัดตามต้นทาง ไม่ใช่ค่าเฉลี่ยจังหวัด; อายุการตรวจวัดยังไม่ยืนยัน'},
    dams:{available:dams.records.length>0,freshness:damFreshness(dams.records,now),fetched_at:dams.records[0]?.fetched_at??null,note:'RID · จำนวนเขื่อนในชุดรายงานที่เชื่อมต่อ ไม่ใช่เขื่อนทุกแห่งในจังหวัด'},
    satellite:{available:floods.available,freshness:floods.query_freshness,fetched_at:floods.fetched_at,note:'GISTDA · ผลลัพธ์ย้อนหลัง 3 วันตามรหัสจังหวัด; ไม่ทราบเวลาถ่ายภาพและไม่ใช่พื้นที่น้ำท่วมรวม'},
  }};
}
