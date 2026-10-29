import {describe,it,expect} from 'vitest';
import {freshness,metricColor,metricValue,contains,chooseForecastDate} from '../lib/semantics';
import {damFreshness} from '../lib/dams';
import {warningState,warningFreshness,warningMapRecords,warningInArea,warningUnmappedCodes} from '../lib/warnings';
import {validatedForecast,validatedWarningFeed,validatedFloodFeed} from '../lib/contracts';
import {floodInArea,floodQueryFreshness,floodColor,floodRecordsInArea,floodResponse,floodRefreshFailure} from '../lib/floods';
import floodFixture from '../../../tests/fixtures/gistda/synthetic-national-feed.json';
import {monitorSource,healthError} from '../lib/source-health';

describe('Source health separates collection, scheduling and source quality',()=>{
  const now=Date.parse('2026-10-29T12:00:00Z');
  it('distinguishes overdue scheduling from an upstream failure and flags a stuck run',()=>{
    const health={last_attempt:'2026-10-29T04:00:00Z',last_success:'2026-10-29T04:10:00Z',status:'SUCCESS'};
    expect(monitorSource('open_meteo_hourly','DELAYED',health,now).state).toBe('OVERDUE');
    expect(monitorSource('open_meteo_hourly','DELAYED',{...health,status:'FAILED'},now)).toMatchObject({state:'FAILED',overdue:true});
    expect(monitorSource('tmd','FRESH',{...health,status:'RUNNING'},now).state).toBe('STALLED');
    expect(monitorSource('tmd','FRESH',{...health,status:'RUNNING',last_attempt:'2026-10-29T11:59:00Z'},now).state).toBe('RUNNING');
  });
  it('keeps planned access separate and source quality visible after a successful run',()=>{
    expect(monitorSource('thaiwater','UNAVAILABLE',null,now)).toMatchObject({state:'PLANNED',needs_attention:false});
    expect(monitorSource('tmd','FRESH',{status:'SUCCESS',last_attempt:'2026-10-29T11:50:00Z',last_success:'2026-10-29T11:51:00Z',quality_issue_count:1},now)).toMatchObject({state:'ATTENTION',quality_issue_count:1});
    expect(monitorSource('gistda','FRESH',{status:'SUCCESS',last_attempt:'2026-10-29T11:00:00Z',last_success:'2026-10-29T11:10:00Z'},now).state).toBe('OK');
  });
  it('uses the actual daily cron slot after a late manual run instead of shifting the schedule',()=>{
    const result=monitorSource('gistda','FRESH',{status:'SUCCESS',last_attempt:'2026-10-29T14:38:00Z',last_success:'2026-10-29T14:43:00Z'},Date.parse('2026-10-30T09:00:00Z'));
    expect(result.expected_by).toBe('2026-10-30T08:27:00.000Z');
    expect(result.state).toBe('OVERDUE');
  });
  it('does not expose arbitrary failure text or link to untrusted workflow URLs',()=>{
    expect(healthError({status:'FAILED',error_summary:'secret credentials'})).not.toContain('secret');
    expect(monitorSource('tmd','STALE',{run_url:'https://private.invalid/secret'},now).run_url).toBeNull();
    expect(monitorSource('tmd','FRESH',{last_attempt:'2099-01-01T00:00:00Z'},now).state).toBe('UNKNOWN');
  });
});
import {areas} from '../lib/geography';
import type {AgencyWarning,DamObservation,Forecast} from '../lib/types';
import {canonicalStoredForecast,geographyIdentityMigrations} from '../lib/geography-migrations';
describe('truthful map semantics',()=>{
  it('does not turn absent data into a zero reading',()=>{expect(metricValue(undefined,'2026-10-25','rainfall_mm')).toBeNull();expect(metricColor(null,'rainfall_mm')).not.toEqual(metricColor(0,'rainfall_mm'));});
  it('uses distinct rainfall and probability scales',()=>{expect(metricColor(25,'rainfall_mm')).not.toEqual(metricColor(25,'rain_probability_pct'));});
  it('cannot make an old forecast fresh through retrieval',()=>{expect(freshness([{fetched_at:'2026-10-28T01:00:00Z',valid_periods:[{valid_start:'2026-10-24T17:00:00Z'}]}] as Forecast[],Date.parse('2026-10-28T02:00:00Z'))).toBe('STALE');});
  it('distinguishes unavailable and unknown',()=>{expect(freshness([])).toBe('UNAVAILABLE');expect(freshness([{fetched_at:'bad',valid_periods:[]}] as unknown as Forecast[])).toBe('UNKNOWN');});
  it('filters by canonical hierarchy, including duplicate names',()=>{const bkk=areas.find(a=>a.id==='TH-P-10')!;const district=areas.find(a=>a.id==='TH-D-1001')!;const other=areas.find(a=>a.id==='TH-P-50')!;expect(contains(bkk,district)).toBe(true);expect(contains(other,district)).toBe(false);});
  it('rejects invalid database documents',()=>{expect(()=>validatedForecast({rainfall_mm:0})).toThrow();});
  it('migrates the verified historical Wiang Kao ID without changing the forecast',()=>{
    const row={location_id:'TH-D-4026',point:{lat:16.725377,lon:102.291901},fetched_at:'2026-10-26T01:00:00Z',
      model_point:{lat:16.72,lon:102.29},valid_periods:[{date:'2026-10-26',rainfall_mm:12.5}]} as Forecast;
    const result=canonicalStoredForecast(row);
    expect(result.location_id).toBe('TH-D-4029');
    expect({...result,location_id:row.location_id}).toEqual(row);
    expect(row.location_id).toBe('TH-D-4026');
    expect(canonicalStoredForecast(result)).toBe(result);
    expect(()=>canonicalStoredForecast({...row,point:{lat:0,lon:0}})).toThrow();
    expect(areas.find(a=>a.id==='TH-D-4029')?.name_th).toBe('เวียงเก่า');
    expect(areas.some(a=>a.id==='TH-D-4026')).toBe(false);
    expect(geographyIdentityMigrations[0].source_as_of).toBe('2023-09-01');
  });
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

describe('GISTDA district query versus observation semantics',()=>{
  const now=Date.parse('2026-10-27T13:00:00Z');
  it('discloses capacity and incomplete refresh failures without echoing private error text',()=>{
    expect(floodRefreshFailure({status:'FAILED',error_summary:'NATIONAL_FEATURE_BUDGET_EXCEEDED'})).toContain('supported number');
    expect(floodRefreshFailure({status:'FAILED',error_summary:'RESPONSE_TOO_LARGE'})).toContain('map data size');
    expect(floodRefreshFailure({status:'FAILED',error_summary:'CANDIDATE_GEOMETRY_LIMIT'})).toContain('map data size');
    expect(floodRefreshFailure({status:'FAILED',error_summary:'DEADLINE_EXCEEDED'})).toContain('time limit');
    expect(floodRefreshFailure({status:'FAILED',error_summary:'PROVIDER_COUNT_CHANGED_DURING_PAGINATION'})).toContain('complete, consistent');
    expect(floodRefreshFailure({status:'FAILED',error_summary:'private credential https://example.invalid/?key=secret'})).toBe('Latest GISTDA refresh failed.');
    expect(floodRefreshFailure({status:'SUCCESS',error_summary:'RESPONSE_TOO_LARGE'})).toBeNull();
    expect(floodRefreshFailure(null)).toBeNull();
  });
  it('keeps a complete empty result available without inventing acquisition or area values',()=>{
    const feed=validatedFloodFeed({...structuredClone(floodFixture),records:[],record_count:0});
    expect(feed.observed_at).toBeNull();expect(feed.area_metrics).toBe('NOT_USED_UNITS_UNVERIFIED');
    expect(floodQueryFreshness(feed,now)).toBe('FRESH');
    expect(feed.record_count).toBe(0);expect(feed.complete_provider_query).toBe(true);
  });
  it('supports every canonical administrative area without a preferred district',()=>{
    const feed=validatedFloodFeed(structuredClone(floodFixture));
    for(const area of areas.filter(a=>a.level!=='basin'))expect(floodInArea(area,feed)).toBe(true);
    expect(()=>validatedFloodFeed({...feed,area_id:'TH-D-1001'})).toThrow();
  });
  it('filters national results by supplied administrative codes across the country without claiming clipping',()=>{
    const feed=validatedFloodFeed({...structuredClone(floodFixture),product_id:'flood_1day_thailand',area_id:'TH',
      query:{limit:100,offset:0},page_count:1,pagination_consistency:'COUNT_AND_DUPLICATES_CHECKED_NO_VERSION_TOKEN',
      records:[{...structuredClone(floodFixture.records[0]),area_ids:['TH-P-10','TH-D-1001']}]});
    const snapshot={feed,records:feed.records,health:null,freshness:'UNKNOWN' as const,query_freshness:'FRESH' as const,storage:'local' as const,error:null};
    for(const id of ['TH','TH-P-10','TH-D-1001','TH-R-CENTRAL'])expect(floodRecordsInArea(snapshot,areas.find(a=>a.id===id)!)).toHaveLength(1);
    for(const id of ['TH-P-26','TH-D-2604','TH-D-5709']){
      const area=areas.find(a=>a.id===id)!;
      expect(floodInArea(area,feed)).toBe(true);
      expect(floodResponse(snapshot,area).status).toBe('EMPTY_RESULT');
      expect(floodRecordsInArea(snapshot,area)).toHaveLength(0);
    }
    expect(()=>validatedFloodFeed({...feed,records:[{...feed.records[0],area_ids:['TH-P-26','TH-D-1001']}]})).toThrow();
  });
  it('validates safe geometry and rejects invented observation dates, alternate products and partial results',()=>{
    const feed=validatedFloodFeed(structuredClone(floodFixture));
    expect(feed.records[0].properties).toBeNull();expect(feed.records[0].geometry.type).toBe('Polygon');
    for(const change of [{record_count:0},{observed_at:'2026-10-27T12:00:00Z'},{product_window:'30days'},{complete_provider_query:false}])
      expect(()=>validatedFloodFeed({...structuredClone(floodFixture),...change})).toThrow();
    const corrupt=structuredClone(floodFixture);corrupt.records[0].geometry.coordinates[0][0]=[0,0];
    expect(()=>validatedFloodFeed(corrupt)).toThrow();
    const polygon=feed.records[0].geometry;
    if(polygon.type!=='Polygon')throw new Error('Expected synthetic polygon fixture');
    const complex=structuredClone(feed);
    complex.records[0].geometry={type:'MultiPolygon',coordinates:Array.from({length:257},()=>polygon.coordinates)};
    expect(()=>validatedFloodFeed(complex)).toThrow();
  });
  it('does not turn a failed or old provider query into a fresh observation',()=>{
    const feed=validatedFloodFeed(structuredClone(floodFixture));
    expect(floodQueryFreshness(feed,now,true)).toBe('DELAYED');
    expect(floodQueryFreshness({...feed,response_at:'2026-10-24T00:00:00Z'},now)).toBe('STALE');
    expect(floodQueryFreshness(null,now)).toBe('UNAVAILABLE');
    expect(floodColor('STALE')).not.toBe(floodColor('FRESH'));
    expect(feed.observed_at).toBeNull();
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
  it('never paints an explicitly flagged provider time conflict as current',()=>{
    const row=message({expires_at:'2026-10-25T06:00:00Z',time_quality:'INVALID_PROVIDER_INTERVAL'});
    expect(warningState(row,[row],now)).toBe('TIME_UNKNOWN');
    expect(warningMapRecords([row],null,'FRESH',now)).toEqual([]);
    expect(warningMapRecords([row],row.warning_id,'FRESH',now)[0]).toMatchObject({display_state:'TIME_UNKNOWN',archived:true});
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
    expect(warningMapRecords([row],null,'DELAYED',now)).toMatchObject([{warning_id:row.warning_id,archived:true,display_state:'CURRENT'}]);
    expect(warningMapRecords([row],null,'STALE',now)).toMatchObject([{archived:true}]);
    expect(warningMapRecords([row],null,'FRESH',now)).toMatchObject([{archived:false}]);
    expect(warningMapRecords([row],row.warning_id,'STALE',now)[0].archived).toBe(true);
  });
  it('uses explicit province codes for regional and local context',()=>{
    const row=message(),province=areas.find(a=>a.id==='TH-P-80')!,district=areas.find(a=>a.province_id==='TH-P-80'&&a.level==='district')!;
    expect(warningInArea(row,province,areas)).toBe(true);
    expect(warningInArea(row,district,areas)).toBe(true);
    expect(warningInArea(row,areas.find(a=>a.id==='TH-P-57')!,areas)).toBe(false);
  });
  it('retains unmapped CAP codes, discloses them and never assigns a guessed province',()=>{
    const row={...message({warning_id:'TMD-unit'}),schema_version:'2.0',source_id:'tmd',product_id:'cap_warnings',data_state:'agency_warning',
      status:'Actual',scope:'Public',fetched_at:'2026-10-26T07:59:00Z',ingested_at:'2026-10-26T08:00:00Z',
      effective_time_source:'CAP effective',language:'th-TH',event:'Test fixture',headline:'Test fixture',description:null,instruction:null,
      agency_severity:'Severe',urgency:'Expected',certainty:'Likely',geometry:null,
      content_ref:'https://www.tmd.go.th/uploads/CAP/CAPTMD-unit.xml',source_url:'https://www.tmd.go.th/api/xml/CAP',terms_url:'https://www.tmd.go.th/content/copyright',
      source_areas:[{description:'Test source area',geocodes:[{value_name:'ISO3166-2',value:'TH-80'},{value_name:'ISO3166-2',value:'R-07'},
        {value_name:'ISO3166-2',value:'R-07'},{value_name:'ISO3166-2',value:'TH-99'}]}]} as AgencyWarning;
    const feed={schema_version:'2.0',source_id:'tmd',product_id:'cap_warnings',data_state:'agency_warning',snapshot_id:'latest',
      fetched_at:row.fetched_at,ingested_at:row.ingested_at,feed_generated_at:row.fetched_at,
      feed_url:row.source_url,feed_copyright:'public domain',feed_item_count:1,ignored_item_count:0,records:[row]};
    expect(validatedWarningFeed(feed).records[0]).toEqual(row);
    expect(warningUnmappedCodes(row)).toEqual([{value_name:'ISO3166-2',value:'R-07'},{value_name:'ISO3166-2',value:'TH-99'}]);
    expect(warningInArea(row,areas.find(a=>a.id==='TH-P-57')!,areas)).toBe(false);
    expect(()=>validatedWarningFeed({...feed,records:[{...row,area_ids:['TH-P-80','TH-P-07']}]})).toThrow();
    expect(()=>validatedWarningFeed({...feed,records:[{...row,area_ids:['TH-P-80','TH-P-99']}]})).toThrow();
  });
});
