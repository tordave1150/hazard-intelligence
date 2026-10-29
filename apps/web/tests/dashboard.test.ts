import {describe,it,expect,vi} from 'vitest';
import {dashboardDates,dashboardMode} from '../lib/dashboard-mode';
import {timeTheme,applyTimeTheme} from '../lib/map-theme';
import {remainingHours,hourlyFreshness,hourlyValue} from '../lib/hourly';
import {metricColor,metricUnit} from '../lib/semantics';
import type {HourlyForecast} from '../lib/types';
import {loadFloodSnapshot} from '../lib/flood-client';
import {validatedFloodChunk} from '../lib/contracts';
import type {FloodFeed,FloodSnapshot} from '../lib/types';
import threeDayFixture from '../../../tests/fixtures/gistda/synthetic-three-day-feed.json';

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
