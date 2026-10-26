import {describe,it,expect} from 'vitest';
import {freshness,metricColor,metricValue,contains,chooseForecastDate} from '../lib/semantics';
import {damFreshness} from '../lib/dams';
import {warningState,warningFreshness,warningMapRecords,warningInArea} from '../lib/warnings';
import {validatedForecast} from '../lib/contracts';
import {areas} from '../lib/geography';
import type {AgencyWarning,DamObservation,Forecast} from '../lib/types';
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
describe('CAP validity and feed freshness',()=>{
  const now=Date.parse('2026-10-26T08:00:00Z');
  const message=(changes:Partial<AgencyWarning>={})=>({sender:'TMD',warning_id:'TMD-a',message_type:'Alert',references:[],issued_at:'2026-10-26T06:00:00Z',
    effective_start:'2026-10-26T06:00:00Z',expires_at:'2026-10-26T09:00:00Z',area_ids:['TH-P-80'],
    geometry:{type:'MultiPolygon',coordinates:[[[[99,8],[100,8],[100,9],[99,8]]]]},...changes} as AgencyWarning);
  it('keeps expired messages expired after a fresh feed fetch',()=>{
    const row=message({expires_at:'2026-10-26T07:00:00Z'});
    expect(warningFreshness({fetched_at:'2026-10-26T07:59:00Z',feed_generated_at:'2026-10-26T07:59:00Z'},now)).toBe('FRESH');
    expect(warningState(row,[row],now)).toBe('EXPIRED');
    expect(warningMapRecords([row],null,'FRESH',now)).toEqual([]);
    expect(warningMapRecords([row],row.warning_id,'FRESH',now)[0].archived).toBe(true);
  });
  it('does not infer current status without expiry or before the effective window',()=>{
    const unknown=message({expires_at:null}),future=message({effective_start:'2026-10-26T08:30:00Z'});
    expect(warningState(unknown,[unknown],now)).toBe('TIME_UNKNOWN');
    expect(warningState(future,[future],now)).toBe('UPCOMING');
    expect(warningMapRecords([unknown,future],null,'FRESH',now)).toEqual([]);
  });
  it('applies exact CAP update and cancellation references',()=>{
    const first=message(),ref={sender:first.sender,warning_id:first.warning_id,issued_at:first.issued_at};
    const update=message({warning_id:'TMD-b',message_type:'Update',references:[ref]});
    expect(warningState(first,[first,update],now)).toBe('SUPERSEDED');
    const cancel=message({warning_id:'TMD-c',message_type:'Cancel',references:[ref]});
    expect(warningState(first,[first,cancel],now)).toBe('CANCELLED');
    cancel.references=[{...ref,issued_at:'2026-10-26T05:00:00Z'}];
    expect(warningState(first,[first,cancel],now)).toBe('CURRENT');
  });
  it('pauses current colors on delayed, failed or stale feeds',()=>{
    const feed={fetched_at:'2026-10-26T07:59:00Z',feed_generated_at:'2026-10-26T07:59:00Z'},row=message();
    expect(warningFreshness(feed,now,true)).toBe('DELAYED');
    expect(warningFreshness({...feed,feed_generated_at:'2026-10-25T07:59:00Z'},now)).toBe('STALE');
    expect(warningFreshness(null,now)).toBe('UNAVAILABLE');
    expect(warningMapRecords([row],null,'DELAYED',now)).toEqual([]);
    expect(warningMapRecords([row],row.warning_id,'STALE',now)[0].archived).toBe(true);
  });
  it('uses explicit province codes for regional and local context',()=>{
    const row=message(),province=areas.find(a=>a.id==='TH-P-80')!,district=areas.find(a=>a.province_id==='TH-P-80'&&a.level==='district')!;
    expect(warningInArea(row,province,areas)).toBe(true);
    expect(warningInArea(row,district,areas)).toBe(true);
    expect(warningInArea(row,areas.find(a=>a.id==='TH-P-57')!,areas)).toBe(false);
  });
});
