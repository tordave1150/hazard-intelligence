import {describe,it,expect,vi} from 'vitest';
import {dashboardDates,dashboardMode} from '../lib/dashboard-mode';
import {timeTheme,applyTimeTheme} from '../lib/map-theme';
import {remainingHours,hourlyFreshness,hourlyValue} from '../lib/hourly';
import {metricColor,metricUnit} from '../lib/semantics';
import type {HourlyForecast} from '../lib/types';
describe('Bangkok calendar and mode',()=>{
  it('keeps Today independent of missing daily forecasts and follows Bangkok rollover',()=>{
    expect(dashboardDates(Date.parse('2026-10-28T16:59:00Z'))).toEqual(['2026-10-28','2026-10-29','2026-10-30','2026-10-31']);
    expect(dashboardDates(Date.parse('2026-10-28T17:00:00Z'))[0]).toBe('2026-10-29');
    expect(dashboardMode('2026-10-28','2026-10-28','situation')).toBe('situation');
    expect(dashboardMode('2026-10-28','2026-10-28','daily')).toBe('daily');
    expect(dashboardMode('2026-10-29','2026-10-28','hourly')).toBe('daily');
  });
  it.each([['04:59','night'],['05:00','dawn'],['06:59','dawn'],['07:00','day'],['16:59','day'],['17:00','dusk'],['18:29','dusk'],['18:30','night'],['00:00','night']])('uses the real Bangkok clock at %s', (clock,theme)=>{
    expect(timeTheme(Date.parse(`2026-10-28T${clock}:00+07:00`))).toBe(theme);
  });
  it('tolerates a pending style and themes only captured basemap layers',()=>{
    const paint=vi.fn();let style:unknown=undefined;
    const map={getStyle:()=>style,setPaintProperty:paint} as unknown as Parameters<typeof applyTimeTheme>[0];
    applyTimeTheme(map,new Set(['land']),'night');expect(paint).not.toHaveBeenCalled();
    style={layers:[{id:'land',type:'background'},{id:'water',type:'fill','source-layer':'water'},
      {id:'gistda-flood-fill',type:'fill'},{id:'warning-cap-line',type:'line'}]};
    applyTimeTheme(map,new Set(['land','water']),'night');
    expect(paint.mock.calls.map(call=>call[0])).toEqual(['land','water']);
  });
});
describe('Today hourly intervals',()=>{
  const start=Date.parse('2026-10-28T00:00:00+07:00');
  const record={forecast_date:'2026-10-28',fetched_at:'2026-10-28T01:00:00Z',valid_hours:Array.from({length:24},(_,i)=>({
    valid_start:new Date(start+i*3600000).toISOString(),valid_end:new Date(start+(i+1)*3600000).toISOString(),rainfall_mm:i,rain_probability_pct:60
  }))} as HourlyForecast;
  it('includes the partly elapsed interval while hiding ended hours and yesterday after midnight',()=>{
    const hours=remainingHours([record],Date.parse('2026-10-28T14:30:00+07:00'));
    expect(hours).toHaveLength(10);expect(hours[0].valid_start).toBe(new Date(start+14*3600000).toISOString());
    expect(remainingHours([record],Date.parse('2026-10-29T00:00:00+07:00'))).toEqual([]);
    expect(hourlyValue(record,hours[0].valid_end,'rainfall_mm')).toBe(14);
  });
  it('keeps hourly amount scales, query age and day rollover distinct from daily forecasts',()=>{
    expect(metricUnit('rainfall_mm','hourly')).toBe('mm / 1h');
    expect(metricColor(5,'rainfall_mm','hourly')).not.toEqual(metricColor(5,'rainfall_mm'));
    expect(hourlyFreshness([record],Date.parse('2026-10-28T02:00:00Z'))).toBe('FRESH');
    expect(hourlyFreshness([record],Date.parse('2026-10-28T02:00:00Z'),true)).toBe('DELAYED');
    expect(hourlyFreshness([record],Date.parse('2026-10-29T00:00:00+07:00'))).toBe('STALE');
  });
});
