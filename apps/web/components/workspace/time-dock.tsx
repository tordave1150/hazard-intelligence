'use client';
import type {ReactNode} from 'react';
import {Clock3,RefreshCw} from 'lucide-react';
import type {MapBackground} from '@/lib/map-layer-state';
import {workspaceBackgroundAvailable} from '@/lib/workspace';
import {hourLabel} from '@/lib/hourly';
import type {HourWindow,Metric} from '@/lib/types';
import styles from './workspace.module.css';
type Hour=HourWindow;
type Props={dates:string[];date:string;today:string;available:Set<string>;geography:'administrative'|'basin';onDate:(date:string)=>void;background:MapBackground;onBackground:(value:MapBackground)=>void;
  metric:Metric;onMetric:(value:Metric)=>void;forecastVisible:boolean;unit:string;hours:Hour[];selectedHour:string;onHour:(value:string)=>void;loading:boolean;onRefresh:()=>void;radar?:ReactNode};
export default function TimeDock(p:Props){
  return <footer className={`timeline ${styles.dock}`} aria-label="Situation and forecast time dock">
    <div className={styles.dockMain}><div className="timeline-label"><Clock3 size={16}/><span><b>Situation / forecast dates</b><small>Asia/Bangkok · calendar dates</small></span></div>
      <div className="timeline-dates">{p.dates.map((date,i)=><button key={date} disabled={p.geography==='basin'&&date!==p.today} aria-pressed={date===p.date} className={date===p.date?'active':''} onClick={()=>p.onDate(date)}>
        <span>{date===p.today?'Today':`+${i}`}</span><b>{new Date(date+'T00:00:00+07:00').toLocaleDateString('en-GB',{timeZone:'Asia/Bangkok',day:'2-digit',month:'short'})}</b><small>{date===p.today?'Situation / forecast':p.available.has(date)?'Daily forecast':'Unavailable'}</small></button>)}</div>
      <label className={styles.displayChoice}>Map background<select aria-label="Map background" value={p.background} onChange={e=>p.onBackground(e.target.value as MapBackground)}>
        <option value="off">{p.date===p.today?'Situation · geography only':'Geography only'}</option><option value="daily" disabled={!workspaceBackgroundAvailable('daily',p.date,p.today,p.geography)}>{p.date===p.today?"Today's daily forecast":'Daily forecast'} · Open-Meteo</option>
        <option value="hourly" disabled={!workspaceBackgroundAvailable('hourly',p.date,p.today,p.geography)}>Today’s hourly forecast · Open-Meteo</option><option value="radar" disabled={!workspaceBackgroundAvailable('radar',p.date,p.today,p.geography)}>Observed radar estimate · TMD</option>
      </select></label>
      {p.forecastVisible&&<label className={styles.displayChoice}>Display metric<select aria-label="Display metric" value={p.metric} onChange={e=>p.onMetric(e.target.value as Metric)}><option value="rainfall_mm">Rainfall · {p.unit}</option><option value="rain_probability_pct">Chance of rain · %</option></select></label>}
      <button className="refresh-button" disabled={p.loading} onClick={p.onRefresh} aria-label="Reload snapshot"><RefreshCw size={16} className={p.loading?'spin':''}/></button>
    </div>
    {p.background==='hourly'&&<div className={styles.hourControl}><label htmlFor="forecast-hour">Forecast interval · Bangkok time</label><select id="forecast-hour" disabled={!p.hours.length} value={p.selectedHour} onChange={e=>p.onHour(e.target.value)}>{!p.hours.length&&<option value="">No applicable interval</option>}{p.hours.map(h=><option key={h.valid_end} value={h.valid_end}>{hourLabel(h)}</option>)}</select><span>Rain is mm/1h · temperature is an instant at interval end.</span></div>}
    {p.radar&&<div className={styles.radarDock} id="radar-time" tabIndex={-1}>{p.radar}</div>}
  </footer>;
}
