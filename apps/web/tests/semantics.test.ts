import {describe,it,expect} from 'vitest';
import {freshness,metricColor,metricValue,contains,chooseForecastDate} from '../lib/semantics';
import {damFreshness} from '../lib/dams';
import {validatedForecast} from '../lib/contracts';
import {areas} from '../lib/geography';
import type {DamObservation,Forecast} from '../lib/types';
describe('truthful map semantics',()=>{
  it('does not turn absent data into a zero reading',()=>{expect(metricValue(undefined,'2026-10-25','rainfall_mm')).toBeNull();expect(metricColor(null,'rainfall_mm')).not.toEqual(metricColor(0,'rainfall_mm'));});
  it('uses distinct rainfall and probability scales',()=>{expect(metricColor(25,'rainfall_mm')).not.toEqual(metricColor(25,'rain_probability_pct'));});
  it('cannot make an old forecast fresh through retrieval',()=>{expect(freshness([{fetched_at:'2026-10-28T01:00:00Z',valid_periods:[{valid_start:'2026-10-24T17:00:00Z'}]}] as Forecast[],Date.parse('2026-10-28T02:00:00Z'))).toBe('STALE');});
  it('distinguishes unavailable and unknown',()=>{expect(freshness([])).toBe('UNAVAILABLE');expect(freshness([{fetched_at:'bad',valid_periods:[]}] as unknown as Forecast[])).toBe('UNKNOWN');});
  it('filters by canonical hierarchy, including duplicate names',()=>{const bkk=areas.find(a=>a.id==='TH-P-10')!;const district=areas.find(a=>a.id==='TH-D-1001')!;const other=areas.find(a=>a.id==='TH-P-50')!;expect(contains(bkk,district)).toBe(true);expect(contains(other,district)).toBe(false);});
  it('rejects invalid database documents',()=>{expect(()=>validatedForecast({rainfall_mm:0})).toThrow();});
  it('defaults to today instead of an older first forecast date',()=>{
    const now=Date.parse('2026-10-26T02:00:00Z');
    expect(chooseForecastDate(['2026-10-25','2026-10-26'],'',now)).toBe('2026-10-26');
    expect(chooseForecastDate(['2026-10-25','2026-10-26'],'2026-10-25',now)).toBe('2026-10-25');
  });
  it('does not refresh an old RID report by retrieving it again',()=>{
    const now=Date.parse('2026-10-26T02:00:00Z');
    expect(damFreshness([{report_date:'2026-10-26',fetched_at:'2026-10-26T01:00:00Z'}] as DamObservation[],now)).toBe('FRESH');
    expect(damFreshness([{report_date:'2026-10-22',fetched_at:'2026-10-26T01:00:00Z'}] as DamObservation[],now)).toBe('STALE');
    expect(damFreshness([{report_date:'2026-10-27',fetched_at:'2026-10-26T01:00:00Z'}] as DamObservation[],now)).toBe('UNKNOWN');
  });
});
