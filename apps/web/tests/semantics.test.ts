import {describe,it,expect} from 'vitest';
import {freshness,metricColor,metricValue,contains,chooseForecastDate} from '../lib/semantics';
import {damFreshness} from '../lib/dams';
import {warningState,warningFreshness,warningMapRecords,warningInArea,warningUnmappedCodes} from '../lib/warnings';
import {validatedForecast,validatedWarningFeed,validatedFloodFeed} from '../lib/contracts';
import {floodInArea,floodQueryFreshness,floodColor} from '../lib/floods';
import floodFixture from '../../../tests/fixtures/gistda/synthetic-feed.json';
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
  it('keeps a complete empty result available without inventing acquisition or area values',()=>{
    const feed=validatedFloodFeed({...structuredClone(floodFixture),records:[],record_count:0});
    expect(feed.observed_at).toBeNull();expect(feed.area_metrics).toBe('NOT_USED_UNITS_UNVERIFIED');
    expect(floodQueryFreshness(feed,now)).toBe('FRESH');
    expect(feed.record_count).toBe(0);expect(feed.complete_provider_query).toBe(true);
  });
  it('restricts scope to Ongkharak and its administrative parents, not neighboring districts',()=>{
    for(const id of ['TH','TH-R-CENTRAL','TH-P-26','TH-D-2604'])expect(floodInArea(areas.find(a=>a.id===id)!)).toBe(true);
    for(const id of ['TH-P-10','TH-D-2601','TH-D-5709'])expect(floodInArea(areas.find(a=>a.id===id)!)).toBe(false);
  });
  it('validates safe geometry and rejects invented observation dates, alternate products and partial results',()=>{
    const feed=validatedFloodFeed(structuredClone(floodFixture));
    expect(feed.records[0].properties).toBeNull();expect(feed.records[0].geometry.type).toBe('Polygon');
    for(const change of [{record_count:0},{observed_at:'2026-10-27T12:00:00Z'},{product_window:'30days'},{complete_provider_query:false}])
      expect(()=>validatedFloodFeed({...structuredClone(floodFixture),...change})).toThrow();
    const corrupt=structuredClone(floodFixture);corrupt.records[0].geometry.coordinates[0][0]=[0,0];
    expect(()=>validatedFloodFeed(corrupt)).toThrow();
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
