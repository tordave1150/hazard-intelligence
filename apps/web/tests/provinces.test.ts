import {describe,it,expect} from 'vitest';
import {buildProvinceOverview} from '../lib/provinces';
import {geometryContains} from '../lib/basin-geometry';
import {areas,areaById} from '../lib/geography';
import {damInArea,damMetadata} from '../lib/dams';
import {gaugeInArea} from '../lib/gauges';
import {loadRainSnapshot} from '../lib/rain-client';
import type {Snapshot,DamSnapshot,GaugeSnapshot,RainSnapshot,WarningSnapshot,AgencyWarning,Forecast} from '../lib/types';
import fixture from '../../../tests/fixtures/thaiwater/normalized-subset.json';
import {validatedGaugeFeed} from '../lib/contracts';
import {validatedRainFeed} from '../lib/contracts';
import rainFixture from '../../../tests/fixtures/thaiwater/normalized-rain-subset.json';
const stamp='2026-10-30T12:00:00Z',now=Date.parse(stamp);
const weather:Snapshot={records:[],status:null,freshness:'UNAVAILABLE',storage:'local',error:null};
const dams:DamSnapshot={records:[],health:null,freshness:'UNAVAILABLE',storage:'local',error:null};
const feed=validatedGaugeFeed(fixture),gauges:GaugeSnapshot={feed,records:feed.records,health:null,freshness:'UNKNOWN',query_freshness:'FRESH',storage:'local',error:null};
const rain:RainSnapshot={feed:null,records:[],health:null,freshness:'UNAVAILABLE',query_freshness:'UNAVAILABLE',storage:'local',error:null};
const warnings:WarningSnapshot={feed:null,records:[],health:null,freshness:'UNAVAILABLE',storage:'local',error:null};
const floods={available:true,counts:{'TH-P-50':0},fetched_at:stamp,query_freshness:'FRESH' as const,generation:'test'};
describe('Province comparison retains all 77 provinces and source meanings',()=>{
  it('separates zero returned features from an unavailable product and a missing measurement',()=>{
    const value=buildProvinceOverview(weather,dams,gauges,warnings,floods,rain,now),row=value.rows.find(r=>r.area_id==='TH-P-50')!;
    expect(value.rows).toHaveLength(77);expect(new Set(value.rows.map(r=>r.area_id)).size).toBe(77);
    expect(row.forecast).toBeNull();expect(row.flood_features).toBe(0);expect(row.rain).toBeNull();expect(row.warnings).toBeNull();
    expect(value.rows.find(r=>r.area_id==='TH-P-37')?.gauges?.count).toBe(0);
    const failed=buildProvinceOverview(weather,dams,gauges,warnings,{...floods,available:false},rain,now);
    expect(failed.rows.every(r=>r.flood_features===null)).toBe(true);
  });
  it('uses a province point forecast for Today and does not borrow a district or previous date',()=>{
    const point={location_id:'TH-P-50',fetched_at:stamp,valid_periods:[{date:'2026-10-30',valid_start:'2026-10-29T17:00:00Z',valid_end:'2026-10-30T17:00:00Z',rainfall_mm:0,rain_probability_pct:0}]} as Forecast;
    const value=buildProvinceOverview({...weather,records:[point]},dams,gauges,warnings,floods,rain,now);
    expect(value.rows.find(r=>r.area_id==='TH-P-50')?.forecast?.rainfall_mm).toBe(0);
    expect(value.rows.find(r=>r.area_id==='TH-P-57')?.forecast).toBeNull();
    expect(buildProvinceOverview({...weather,records:[point]},dams,gauges,warnings,floods,rain,now+86400000).rows.every(r=>r.forecast===null)).toBe(true);
  });
  it('keeps an invalid CAP interval out of the current warning count',()=>{
    const common:AgencyWarning={schema_version:'2.0',source_id:'tmd',product_id:'cap_warnings',data_state:'agency_warning',
      warning_id:'test',sender:'TMD',message_type:'Alert',status:'Actual',scope:'Public',references:[],area_ids:['TH-P-50'],issued_at:stamp,
      fetched_at:stamp,ingested_at:stamp,effective_start:'2026-10-30T10:00:00Z',expires_at:'2026-10-30T14:00:00Z',effective_time_source:'CAP effective',
      language:'th',event:'Rain',headline:'Rain',description:null,instruction:null,agency_severity:'Severe',urgency:'Expected',certainty:'Likely',
      source_areas:[],geometry:null,content_ref:'https://www.tmd.go.th/uploads/CAP/CAPTMD1.xml',source_url:'https://www.tmd.go.th/api/xml/CAP',terms_url:'https://www.tmd.go.th/content/copyright'};
    const messages=[common,{...common,warning_id:'invalid',expires_at:'2026-10-30T09:00:00Z',time_quality:'INVALID_PROVIDER_INTERVAL' as const}];
    const value=buildProvinceOverview(weather,dams,gauges,{...warnings,feed:{fetched_at:stamp,feed_generated_at:stamp} as NonNullable<WarningSnapshot['feed']>,records:messages},floods,rain,now);
    expect(value.rows.find(r=>r.area_id==='TH-P-50')?.warnings).toEqual({current:1,upcoming:0,time_unknown:1});
    expect(value.rows.find(r=>r.area_id==='TH-P-50')?.data_gaps).toContain('warnings');
  });
});
describe('Basin context does not infer geographic membership',()=>{
  it('preserves 77 provinces, adds 22 separate basins and maps all 35 published dams once',()=>{
    const basins=areas.filter(a=>a.level==='basin');expect(basins).toHaveLength(22);expect(areas.filter(a=>a.level==='province')).toHaveLength(77);
    for(const dam of damMetadata)expect(basins.filter(b=>damInArea(dam,b))).toHaveLength(1);
    const row={...feed.records[0],basin_id:'TH-B-13'};
    expect(gaugeInArea(row,areaById.get('TH-B-13')!)).toBe(true);expect(gaugeInArea({...row,basin_id:null},areaById.get('TH-B-13')!)).toBe(false);
  });
  it('respects polygon holes, multipolygons and non-finite points',()=>{
    const shape={type:'Polygon' as const,coordinates:[[[0,0],[4,0],[4,4],[0,4],[0,0]],[[1,1],[3,1],[3,3],[1,3],[1,1]]]};
    expect(geometryContains(shape,{lat:.5,lon:.5})).toBe(true);expect(geometryContains(shape,{lat:2,lon:2})).toBe(false);
    expect(geometryContains({type:'MultiPolygon',coordinates:[shape.coordinates]},{lat:.5,lon:.5})).toBe(true);
    expect(geometryContains(shape,{lat:NaN,lon:1})).toBe(false);
  });
});
describe('Rain station polling avoids repeated national downloads',()=>{
  it('validates source rain units and preserves measured zero and unknown UTC bounds',()=>{
    const value=validatedRainFeed(rainFixture);
    expect(value.records[1].rain_24h_mm).toBe(0);expect(value.window_start).toBeNull();expect(value.records.every(r=>r.observed_at===null)).toBe(true);
    const bad=structuredClone(rainFixture);bad.records[0].observed_at='2026-10-30T16:00:00Z' as never;
    expect(()=>validatedRainFeed(bad)).toThrow();
  });
  it('retains a complete matching generation and refreshes metadata only',async()=>{
    const previous={...rain,feed:{fetched_at:stamp,record_count:1} as RainSnapshot['feed'],detail_loaded:true,records:[{gauge_id:'THR-1'}] as RainSnapshot['records']};let calls=0;
    const request=(async()=>{calls++;return new Response(JSON.stringify({...previous,records:[],detail_loaded:false}));}) as typeof fetch;
    const value=await loadRainSnapshot(previous,true,new AbortController().signal,request);
    expect(calls).toBe(1);expect(value.records).toEqual(previous.records);expect(value.detail_loaded).toBe(true);
  });
  it('does not present old stations as a new summary generation',async()=>{
    const previous={...rain,feed:{fetched_at:stamp} as RainSnapshot['feed'],detail_loaded:true,records:[{gauge_id:'THR-1'}] as RainSnapshot['records']};
    const request=(async()=>new Response(JSON.stringify({...rain,feed:{fetched_at:'2026-10-30T14:00:00Z',record_count:0},detail_loaded:false}))) as typeof fetch;
    const value=await loadRainSnapshot(previous,false,new AbortController().signal,request);
    expect(value.records).toEqual([]);expect(value.detail_loaded).toBe(false);
  });
});
