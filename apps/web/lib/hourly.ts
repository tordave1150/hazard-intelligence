import {bangkokDate,bangkokTime} from './semantics';
import type {Freshness,HourlyForecast,HourWindow,Metric} from './types';
export function hourlyFreshness(records:HourlyForecast[],now=Date.now(),failed=false):Freshness{
  if(!records.length)return 'UNAVAILABLE';
  const times=records.map(r=>Date.parse(r.fetched_at));
  if(times.some(t=>!Number.isFinite(t)||t>now+300000))return 'UNKNOWN';
  if(records.some(r=>r.forecast_date!==bangkokDate(now)))return 'STALE';
  const age=(now-Math.min(...times))/3600000;
  return age<=6&&!failed?'FRESH':age<=10?'DELAYED':'STALE';
}
export const remainingHours=(records:HourlyForecast[],now:number,windows:HourWindow[]=records[0]?.valid_hours??[])=>records[0]?.forecast_date===bangkokDate(now)?windows.filter(h=>Date.parse(h.valid_end)>now):[];
export const hourlyValue=(record:HourlyForecast|undefined,end:string,metric:Metric)=>record?.valid_hours.find(h=>h.valid_end===end)?.[metric]??null;
export const hourLabel=(hour:HourWindow)=>`${bangkokTime(hour.valid_start)} – ${bangkokTime(hour.valid_end)}`;
