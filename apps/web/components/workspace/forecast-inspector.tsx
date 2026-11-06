import {ArrowDownToLine,Clock3,Info} from 'lucide-react';
import {bangkokTime} from '@/lib/semantics';
import type {Area,Forecast,Freshness} from '@/lib/types';
import styles from './workspace.module.css';
export default function ForecastInspector({area,current,date,scopeCount,status,oldestFetch,firstValid,loading,failed,onExport}:{area:Area;current?:Forecast;date:string;scopeCount:number;status:Freshness;oldestFetch:string|null;firstValid?:string;loading:boolean;failed:boolean;onExport?:()=>void}){
  const period=current?.valid_periods.find(p=>p.date===date);
  return <section className="evidence-card" aria-label="Daily forecast evidence"><div className="evidence-heading"><b>{area.name}</b><span className="mini-tag">FORECAST</span></div>
    {period&&current?<><div className="area-value">{period.rainfall_mm==null?'—':period.rainfall_mm.toFixed(1)}<span>mm / 24h</span></div><p className="value-caption">Forecast rainfall · {date}</p>
      <div className="weather-pair"><span>Chance of rain<b>{period.rain_probability_pct==null?'No data':`${period.rain_probability_pct}%`}</b></span><span>Temperature<b>{period.temp_min_c==null||period.temp_max_c==null?'No data':`${period.temp_min_c}–${period.temp_max_c}°C`}</b></span></div>
      <div className={`mini-chart ${styles.forecastBars}`} aria-label="Daily forecast rainfall values">{current.valid_periods.map(p=><div data-selected={p.date===date} key={p.date}><span>{p.rainfall_mm??'—'}</span><i style={{height:p.rainfall_mm==null?2:Math.max(3,Math.min(50,p.rainfall_mm*1.2))}}/><small>{new Date(p.date+'T00:00:00+07:00').toLocaleDateString('en-GB',{timeZone:'Asia/Bangkok',day:'2-digit',month:'short'})}</small></div>)}</div>
      <p className="coverage-note"><Info size={12}/>{current.spatial_method}. Requested {current.point.lat.toFixed(3)}°N, {current.point.lon.toFixed(3)}°E. Returned grid {current.model_point.lat.toFixed(3)}°N, {current.model_point.lon.toFixed(3)}°E.</p>
      <dl className="time-details"><dt>Valid window</dt><dd>{bangkokTime(period.valid_start)} – {bangkokTime(period.valid_end)}</dd><dt>Model issue time</dt><dd>Not supplied by provider</dd><dt>Retrieved</dt><dd>{bangkokTime(current.fetched_at)}</dd><dt>Quality</dt><dd>{current.quality_status}</dd></dl>
    </>:<div className="region-outlook"><strong>{scopeCount}</strong><p>{scopeCount?'forecast points in this area. Select a province or district for its point forecast.':'No applicable forecast available for this date/area.'}</p></div>}
    <div className="freshness-card"><div><Clock3 size={15}/><b>Daily forecast snapshot</b><span className={`freshness ${status.toLowerCase()}`}>{loading?'LOADING':status}</span></div><small>Oldest retrieval: {bangkokTime(oldestFetch)}</small><small>First valid window: {bangkokTime(firstValid)}</small>{failed&&<p className="failed-run">Latest ingestion failed · showing the previous complete snapshot.</p>}</div>
    {onExport&&<button className="export-button" onClick={onExport}><ArrowDownToLine size={14}/>Export this area’s weather</button>}
    <a className="source-link" href="https://open-meteo.com/" target="_blank" rel="noreferrer">Weather data by Open-Meteo</a>
  </section>;
}
