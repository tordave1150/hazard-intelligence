import {effectiveBackground,backgroundAvailable} from '../lib/map-layer-state';
import {orderMapLayers,mapLayerAnchors} from '../lib/map-layer-order';
import {describe,it,expect,vi} from 'vitest';
import {dashboardDates,dashboardMode} from '../lib/dashboard-mode';
import {timeTheme,applyTimeTheme,placeLabelOpacity,riverLineWidth,type TimeTheme,type CountryFocus} from '../lib/map-theme';
import {createExpression} from '@maplibre/maplibre-gl-style-spec';
import {damStorageSymbol,damMarkerSvg} from '../lib/map-dams';
import {remainingHours,hourlyFreshness,hourlyValue} from '../lib/hourly';
import {metricColor,metricUnit} from '../lib/semantics';
import type {HourlyForecast} from '../lib/types';
import {loadFloodSnapshot} from '../lib/flood-client';
import {validatedFloodChunk} from '../lib/contracts';
import type {FloodFeed,FloodSnapshot} from '../lib/types';
import threeDayFixture from '../../../tests/fixtures/gistda/synthetic-three-day-feed.json';
import {buildFloodAreaIndex} from '../lib/flood-area-index';
import {floodResultCount} from '../lib/floods';
import {areaById} from '../lib/geography';

describe('Complete three-day GISTDA loading',()=>{
  const full=threeDayFixture as FloodFeed;
  const {records,...metadata}=full;
  const page=(chunk:number,changes:Partial<FloodSnapshot>={}):FloodSnapshot=>({
    feed:structuredClone(metadata),records:structuredClone(records.slice(chunk*2,chunk*2+2)),
    health:{status:'SUCCESS'},freshness:'UNKNOWN',query_freshness:'FRESH',storage:'mongo',error:null,
    pagination:{generation:'test-generation',chunk,chunk_count:2,next_chunk:chunk===0?1:null,complete:false},...changes});
  function fetchPages(values:FloodSnapshot[]){
    let index=0;
    return vi.fn(async()=>({ok:true,json:async()=>values[index++]})) as unknown as typeof fetch;
  }
  it('assembles every page from one generation and retains explicit three-day/unknown acquisition labels',async()=>{
    const fetcher=fetchPages([page(0),page(1)]);
    const result=await loadFloodSnapshot(new AbortController().signal,fetcher);
    expect(result.records).toHaveLength(3);expect(result.pagination?.complete).toBe(true);
    expect(result.feed?.product_window).toBe('3days');expect(result.feed?.observed_at).toBeNull();
    expect(fetcher).toHaveBeenCalledTimes(2);
    expect(vi.mocked(fetcher).mock.calls[1][0]).toContain('chunk=1&generation=test-generation');
  });
  it('does not redownload unchanged geometry on the five-minute health poll',async()=>{
    const previous=await loadFloodSnapshot(new AbortController().signal,fetchPages([page(0),page(1)]));
    const fetcher=fetchPages([page(0,{health:{status:'FAILED'},query_freshness:'DELAYED'})]);
    const result=await loadFloodSnapshot(new AbortController().signal,fetcher,previous);
    expect(fetcher).toHaveBeenCalledTimes(1);expect(result.records).toHaveLength(3);
    expect(result.health?.status).toBe('FAILED');expect(result.query_freshness).toBe('DELAYED');
  });
  it('loads a national count without downloading geometry or treating an unloaded view as empty',async()=>{
    const summary=page(0,{records:[],scope:{area_id:'TH',record_count:3,mode:'summary'},
      pagination:{generation:'test-generation',chunk:0,chunk_count:1,next_chunk:null,complete:false}});
    const fetcher=fetchPages([summary]);
    const result=await loadFloodSnapshot(new AbortController().signal,fetcher,undefined,{areaId:'TH',mode:'summary'});
    expect(fetcher).toHaveBeenCalledTimes(1);expect(result.records).toHaveLength(0);
    expect(floodResultCount(result,areaById.get('TH')!)).toBe(3);
    expect(floodResultCount(result,areaById.get('TH-P-26')!)).toBeNull();
    expect(String(vi.mocked(fetcher).mock.calls[0][0])).toContain('view=summary');
  });
  it('checks scoped totals rather than the national total and rejects mismatched areas',async()=>{
    const scoped=page(0,{records:records.slice(0,1),scope:{area_id:'TH-P-26',record_count:1,mode:'detail'},
      pagination:{generation:'test-generation',chunk:0,chunk_count:1,next_chunk:null,complete:true}});
    const result=await loadFloodSnapshot(new AbortController().signal,fetchPages([scoped]),undefined,{areaId:'TH-P-26',mode:'detail'});
    expect(result.records).toHaveLength(1);expect(result.feed?.record_count).toBe(3);
    await expect(loadFloodSnapshot(new AbortController().signal,fetchPages([scoped]),undefined,{areaId:'TH-P-25',mode:'detail'})).rejects.toThrow();
    await expect(loadFloodSnapshot(new AbortController().signal,fetchPages([{...scoped,records:[]}]),undefined,{areaId:'TH-P-26',mode:'detail'})).rejects.toThrow();
  });
  it('builds a geometry-free page index with deduplicated ancestors and no guessed district coverage',()=>{
    const rows=[{chunk_id:'0000',records:[{id:'one',area_ids:['TH-P-26','TH-D-2604']},{id:'two',area_ids:['TH-P-26']}]},
      {chunk_id:'0001',records:[{id:'three',area_ids:['TH-P-25','TH-D-2501']}]}];
    const index=buildFloodAreaIndex(rows,3,2);
    expect(index.get('TH')).toEqual({count:3,chunks:[0,1]});
    expect(index.get('TH-P-26')).toEqual({count:2,chunks:[0]});
    expect(index.get('TH-D-2604')).toEqual({count:1,chunks:[0]});
    expect(index.has('TH-D-2601')).toBe(false);
    expect(()=>buildFloodAreaIndex(rows,4,2)).toThrow();
    expect(()=>buildFloodAreaIndex([...rows,rows[0]],5,3)).toThrow();
    expect(()=>buildFloodAreaIndex([{chunk_id:'0000',records:[{id:'one'},{id:'one'}]}],2,1)).toThrow();
  });
  it('bounds concurrent requests to four while preserving page order',async()=>{
    let active=0,maximum=0;
    const fetcher=vi.fn(async(url:RequestInfo|URL)=>{
      active++;maximum=Math.max(maximum,active);
      const index=Number(new URL(String(url),'https://example.invalid').searchParams.get('chunk')??0);
      await new Promise(resolve=>setTimeout(resolve,1));active--;
      const row=structuredClone(records[index%records.length]);row.id=row.id.split('-')[0]+'-'+index;
      return {ok:true,json:async()=>page(index,{feed:{...metadata,record_count:6},records:[row],
        pagination:{generation:'test-generation',chunk:index,chunk_count:6,next_chunk:index<5?index+1:null,complete:false}})};
    }) as unknown as typeof fetch;
    const result=await loadFloodSnapshot(new AbortController().signal,fetcher);
    expect(maximum).toBe(4);expect(fetcher).toHaveBeenCalledTimes(6);
    expect(result.records.map(row=>row.id.split('-').at(-1))).toEqual(['0','1','2','3','4','5']);
  });
  it.each(['generation','duplicate','missing','cursor','metadata'])('rejects %s corruption before returning anything to the map',async(corruption)=>{
    const first=page(0),second=page(1);
    if(corruption==='generation')second.pagination!.generation='different-generation';
    if(corruption==='duplicate')second.records=[first.records[0]];
    if(corruption==='missing')second.records=[];
    if(corruption==='cursor')first.pagination!.next_chunk=0;
    if(corruption==='metadata')second.feed!.response_at='2026-10-28T00:00:00Z';
    await expect(loadFloodSnapshot(new AbortController().signal,fetchPages([first,second]))).rejects.toThrow();
  });
  it('validates a bounded stored chunk without treating it as a complete feed',()=>{
    const chunk={source_id:'gistda',product_id:'flood_3days_thailand',chunk_id:'0000',chunk_count:2,
      feed:metadata,records:records.slice(0,2)};
    expect(validatedFloodChunk(chunk).feed.record_count).toBe(3);
    expect(()=>validatedFloodChunk({...chunk,chunk_id:'0002'})).toThrow();
    expect(()=>validatedFloodChunk({...chunk,records:[]})).toThrow();
    expect(()=>validatedFloodChunk({...chunk,feed:{...metadata,product_window:'1day'}})).toThrow();
    const bad=structuredClone(chunk);bad.records[0].geometry.coordinates=[];
    expect(()=>validatedFloodChunk(bad)).toThrow();
  });
});
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
describe('Basemap context preserves scientific layers',()=>{
  const country:CountryFocus={type:'Feature',properties:{role:'country'},geometry:{type:'Polygon',coordinates:[[[97,5],[106,5],[106,21],[97,21],[97,5]]]}};
  it.each(['dawn','day','dusk','night'] as TimeTheme[])('changes captured base layers only in %s',theme=>{
    const paint=vi.fn(),base=new Set(['waterway','city','road']);
    const style={layers:[{id:'waterway',type:'line','source-layer':'waterway'},
      {id:'city',type:'symbol','source-layer':'place',layout:{'text-field':['get','name'],'icon-image':'point'}},
      {id:'road',type:'line','source-layer':'transportation'},
      {id:'weather-native-fill',type:'fill'},{id:'gistda-flood-fill',type:'fill'},
      {id:'warning-cap-line',type:'line'},{id:'gauge-point',type:'circle'}]};
    const map={getStyle:()=>style,setPaintProperty:paint} as unknown as Parameters<typeof applyTimeTheme>[0];
    applyTimeTheme(map,base,theme,country);
    expect(paint.mock.calls.every(([id])=>base.has(id))).toBe(true);
    expect(paint).toHaveBeenCalledWith('waterway','line-width',riverLineWidth);
    expect(paint).toHaveBeenCalledWith('city','text-opacity',placeLabelOpacity(country));
    expect(createExpression(placeLabelOpacity(country)).result).toBe('success');
  });
  it('emphasizes source-class rivers without inventing stream order or small low-zoom waterways',()=>{
    const compiled=createExpression(riverLineWidth);if(compiled.result!=='success')throw Error();
    expect(compiled.value.evaluate({zoom:4},{type:2,properties:{class:'river'}})).toBeGreaterThan(1);
    expect(compiled.value.evaluate({zoom:4},{type:2,properties:{class:'stream'}})).toBe(0);
    expect(compiled.value.evaluate({zoom:10},{type:2,properties:{class:'stream'}})).toBeGreaterThan(0);
  });
});
describe('Dam rings describe normal storage capacity',()=>{
  it('distinguishes missing percent from a reported zero',()=>{
    expect(damStorageSymbol(null)).toMatchObject({percent:null,fraction:null,overNormal:false});
    expect(damStorageSymbol(0)).toMatchObject({percent:0,fraction:0,overNormal:false});
    expect(damMarkerSvg(null)).toContain('>?</text>');expect(damMarkerSvg(0)).not.toContain('>?</text>');
  });
  it('bounds only the ring while preserving an above-normal reported percentage',()=>{
    expect(damStorageSymbol(123.45)).toEqual({percent:123.45,fraction:1,overNormal:true,label:'123.45% of normal storage capacity'});
    expect(damMarkerSvg(123.45)).toContain('>+</text>');
    expect(damStorageSymbol(50).fraction).toBe(.5);
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


describe('Forecast background availability',()=>{
  it('resolves exactly one fill and respects Off, Situation and basin scope',()=>{
    for(const mode of ['situation','daily','hourly'] as const){
      expect(effectiveBackground(mode,false,'administrative')).toBe('off');
      expect(effectiveBackground(mode,true,'basin')).toBe('off');
    }
    expect(effectiveBackground('situation',true,'administrative')).toBe('off');
    expect(effectiveBackground('daily',true,'administrative')).toBe('daily');
    expect(effectiveBackground('hourly',true,'administrative')).toBe('hourly');
  });
  it('allows future daily forecasts but never future hourly or basin forecast fills',()=>{
    expect(backgroundAvailable('daily','2026-11-02','2026-11-01','administrative')).toBe(true);
    expect(backgroundAvailable('hourly','2026-11-02','2026-11-01','administrative')).toBe(false);
    expect(backgroundAvailable('hourly','2026-11-01','2026-11-01','administrative')).toBe(true);
    for(const background of ['daily','hourly'] as const)expect(backgroundAvailable(background,'2026-11-01','2026-11-01','basin')).toBe(false);
    expect(backgroundAvailable('off','2026-11-02','2026-11-01','basin')).toBe(true);
  });
});

describe('Shared native/deck layer order',()=>{
  it.each([true,false])('keeps forecast below river/place context and observation overlays (basemap=%s)',(withContext)=>{
    const base=withContext?[{id:'land',type:'fill'},{id:'river',type:'line','source-layer':'waterway'},{id:'place',type:'symbol'}]:[{id:'land',type:'background'}];
    const ids=[...base.map(l=>l.id),'weather-native-fill','weather-native-line','weather-native-extrusion',mapLayerAnchors.forecast,'radar-image-layer','gistda-flood-fill','gistda-flood-line','warning-cap-fill','warning-cap-line','gauge-clusters','gauge-cluster-count','gauge-point'];
    const styleLayers=[...base,...ids.slice(base.length).map(id=>({id,type:'fill'}))];
    const moveLayer=vi.fn((id:string,before?:string)=>{ids.splice(ids.indexOf(id),1);ids.splice(before?ids.indexOf(before):ids.length,0,id);});
    orderMapLayers({getStyle:()=>({layers:styleLayers}),moveLayer} as unknown as Parameters<typeof orderMapLayers>[0],new Set(base.map(l=>l.id)));
    const below=(a:string,b:string)=>expect(ids.indexOf(a)).toBeLessThan(ids.indexOf(b));
    below('weather-native-extrusion',mapLayerAnchors.forecast);
    below(mapLayerAnchors.forecast,'radar-image-layer');below('radar-image-layer','gistda-flood-fill');
    if(withContext){below(mapLayerAnchors.forecast,'river');below('river','place');below('place','gistda-flood-fill');}
    below('gistda-flood-line',mapLayerAnchors.flood);below('warning-cap-line',mapLayerAnchors.cap);below(mapLayerAnchors.cap,'gauge-point');
    expect(moveLayer.mock.calls.some(([id])=>id==='land'||id.startsWith('gauge')||id.startsWith('warning')||id.startsWith('gistda'))).toBe(false);
  });
});
