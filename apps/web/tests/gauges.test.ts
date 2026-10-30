import {describe,it,expect} from 'vitest';
import fixture from '../../../tests/fixtures/thaiwater/normalized-subset.json';
import {validatedGaugeFeed} from '../lib/contracts';
import {gaugeResponse,gaugeInArea,gaugeQueryFreshness,gaugeValue} from '../lib/gauges';
import {parseGaugeHistory,wallOrdinal} from '../lib/gauge-history-data';
import {areaById} from '../lib/geography';
import {monitorSource} from '../lib/source-health';
import type {GaugeSnapshot,GaugeHistory} from '../lib/types';

describe('National HII stations preserve measurement meaning',()=>{
  const feed=validatedGaugeFeed(fixture),snapshot:GaugeSnapshot={feed,records:feed.records,health:null,freshness:'UNKNOWN',query_freshness:'FRESH',storage:'local',error:null};
  it('filters each returned province and district without a local allowlist',()=>{
    expect(gaugeResponse(snapshot,areaById.get('TH')!).records).toHaveLength(2);
    for(const row of feed.records){
      expect(gaugeInArea(row,areaById.get(row.province_id)!)).toBe(true);
      expect(gaugeInArea(row,areaById.get(row.region_id)!)).toBe(true);
      if(row.district_id)expect(gaugeInArea(row,areaById.get(row.district_id)!)).toBe(true);
      const other=feed.records.find(r=>r.province_id!==row.province_id)!;
      expect(gaugeInArea(row,areaById.get(other.province_id)!)).toBe(false);
    }
  });
  it('distinguishes an empty area, unavailable product and measured zero',()=>{
    expect(gaugeResponse(snapshot,areaById.get('TH-P-37')!)).toMatchObject({status:'EMPTY_RESULT',selected_count:0,freshness:'UNKNOWN'});
    expect(gaugeResponse(snapshot,areaById.get('TH')!,'rain')).toMatchObject({status:'UNAVAILABLE',records:[]});
    expect(gaugeValue(null)).toBe('ไม่ระบุ');expect(gaugeValue(0)).toBe('0.00');
  });
  it('fresh collection never assigns observation UTC or a current station age',()=>{
    expect(gaugeQueryFreshness(feed,Date.parse(feed.fetched_at)+1000)).toBe('FRESH');
    expect(snapshot.freshness).toBe('UNKNOWN');expect(feed.records.every(r=>r.observed_at===null)).toBe(true);
    expect(gaugeQueryFreshness(feed,Date.parse(feed.fetched_at)+1000,true)).toBe('DELAYED');
    expect(monitorSource('thaiwater','FRESH',{status:'SUCCESS',last_attempt:feed.fetched_at,last_success:feed.ingested_at},Date.parse(feed.ingested_at)+1000)).toMatchObject({state:'OK',cadence_hours:2,quality_issue_count:0});
  });
  it('rejects lost rows, invented UTC, invalid dates and false coverage',()=>{
    for(const mutate of [
      (v:any)=>v.records.pop(),(v:any)=>v.records[0].observed_at=v.fetched_at,
      (v:any)=>v.records[0].source_observed_at='2026-02-30 12:00',(v:any)=>v.coverage_by_province=[],
    ]){const value=structuredClone(fixture);mutate(value);expect(()=>validatedGaugeFeed(value)).toThrow();}
  });
});
describe('Selected station history uses provider calendar times and gaps',()=>{
  const context:Omit<GaugeHistory,'points'|'invalid_value_count'>={gauge_id:'THW-737',source_id:'thaiwater',unit:'m above mean sea level',observation_time_status:'TIMEZONE_NOT_SUPPLIED',fetched_at:'2026-10-29T16:38:43Z',start_date:'2026-10-27',end_date:'2026-10-29',source_url:'https://api-v3.thaiwater.net/api/v1/thaiwater30/public/waterlevel_graph'};
  const parse=(rows:unknown[])=>parseGaugeHistory({result:'OK',data:{graph_data:rows}},context);
  it('sorts original wall times, preserves zero/negative/null and flags invalid values',()=>{
    const value=parse([{datetime:'2026-10-29 10:00',value:null},{datetime:'2026-10-27 10:00',value:0},{datetime:'2026-10-28 10:00',value:-1.2},{datetime:'2026-10-29 11:00',value:'invalid'}]);
    expect(value.points.map(p=>p.value)).toEqual([0,-1.2,null,null]);expect(value.invalid_value_count).toBe(1);
    expect(value.points[0].source_observed_at).toBe('2026-10-27 10:00');
  });
  it('rejects duplicate or impossible calendar dates and out-of-window data',()=>{
    expect(()=>wallOrdinal('2026-02-30 12:00')).toThrow();
    for(const rows of [[{datetime:'2026-10-30 00:00',value:1}],[{datetime:'2026-10-27 00:00',value:1},{datetime:'2026-10-27 00:00',value:2}]])expect(()=>parse(rows)).toThrow();
  });
});
