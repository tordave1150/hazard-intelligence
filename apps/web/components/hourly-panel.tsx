'use client';
import type {Area,HourlySnapshot} from '@/lib/types';
import {contains,bangkokTime} from '@/lib/semantics';
import {areaById} from '@/lib/geography';
import {remainingHours,hourLabel,hourlyFreshness} from '@/lib/hourly';
type Props={area:Area;snapshot:HourlySnapshot;now:number;selectedEnd:string;loading:boolean;onHour:(end:string)=>void};
export default function HourlyPanel({area,snapshot,now,selectedEnd,loading,onHour}:Props){
  const hours=remainingHours(snapshot.records,now,snapshot.available_hours),hour=hours.find(h=>h.valid_end===selectedEnd)??hours[0];
  const scoped=snapshot.records.filter(r=>contains(area,areaById.get(r.location_id)!));
  const point=scoped.find(r=>r.location_id===area.id),value=point?.valid_hours.find(h=>h.valid_end===hour?.valid_end);
  const freshness=hourlyFreshness(snapshot.records,now,snapshot.health?.status==='FAILED');
  return <section className="situation-evidence" aria-label="Today's hourly forecast"><h3>Today's hourly forecast <span className="mini-tag">FORECAST</span></h3>
    <p>Open-Meteo · representative points · snapshot {freshness}. Scheduled refresh every 4 hours; model issue time is not supplied.</p>
    {loading&&<p role="status">Loading the stored hourly forecast…</p>}
    {!hours.length?<p role="status">{loading?'Checking today’s available intervals.':snapshot.error??'No applicable hourly forecast for today is available. Daily forecasts remain accessible.'}</p>:<>
      <label htmlFor="forecast-hour">Forecast interval · Bangkok time</label><select id="forecast-hour" value={hour.valid_end} onChange={e=>onHour(e.target.value)}>{hours.map(h=><option key={h.valid_end} value={h.valid_end}>{hourLabel(h)}</option>)}</select>
      {Date.parse(hour.valid_start)<now&&<p>Part of this interval has elapsed. Values describe the full hour, not just its remaining minutes.</p>}
      <p>{value?`Rain ${value.rainfall_mm??'unavailable'} mm / 1h · chance ${value.rain_probability_pct??'unavailable'}% · temperature ${value.temperature_c??'unavailable'} °C at ${bangkokTime(value.temperature_valid_at)}`:`${scoped.length} forecast points in this area. Select a province or district for its point values.`}</p>
      <p>Rain and probability apply to {hourLabel(hour)}. Temperature is an instant at the interval end. Retrieved {bangkokTime(point?.fetched_at??scoped[0]?.fetched_at)}.</p>
      {snapshot.health?.status==='FAILED'&&<p role="status">Latest hourly refresh failed; retaining the last complete snapshot.</p>}
      {freshness!=='FRESH'&&<p role="status">The snapshot is {freshness.toLowerCase()}; map colors are paused for stale or unknown timing.</p>}
      {snapshot.storage==='local'&&<p>LOCAL PREVIEW · not a production snapshot.</p>}
    </>}
  </section>;
}
