import {beforeEach,describe,it,expect,vi} from 'vitest';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {encode} from '@msgpack/msgpack';
import {areaById} from '../lib/geography';
import {checkedWindowFeed,checkedWindowManifest,type FloodManifest} from '../lib/flood-window-contract';
import {loadFloodSnapshot} from '../lib/flood-client';
import type {FloodWindow,FloodFeature} from '../lib/types';
const mocks=vi.hoisted(()=>({readFile:vi.fn(),database:vi.fn(),uri:null as string|null}));
vi.mock('../lib/mongo',()=>({mongoUri:()=>mocks.uri,mongoDatabase:mocks.database}));
vi.mock('node:fs/promises',()=>({readFile:mocks.readFile}));
import {decodedFloodObject,readWindowSnapshot} from '../lib/flood-window-server';

function fixture(count:number,window:FloodWindow='30days'){
  const province='TH-P-10',district='TH-D-1001',region=areaById.get(province)!.region_id!,chunks:FloodManifest['chunks']=[],objects:Record<string,string>={};
  const stamp=new Date().toISOString(),manifest:FloodManifest={_id:'11111111-1111-4111-8111-111111111111',storage_version:'gzip-v1',product_window:window,
    feed:{schema_version:'3.0',source_id:'gistda',product_id:('flood_'+window+'_thailand') as 'flood_30days_thailand',product_window:window,data_state:'satellite_observation',snapshot_id:'latest',
      area_id:'TH',query:{limit:1000,offset:0},page_count:Math.max(1,Math.ceil(count/1000)),pagination_consistency:'COUNT_AND_DUPLICATES_CHECKED_NO_VERSION_TOKEN',source_url:'https://api-gateway.gistda.or.th/api/2.0/resources/features/flood/'+window,
      attribution:'GISTDA Disaster Platform',response_at:stamp,fetched_at:stamp,ingested_at:stamp,observed_at:null,observation_time_status:'NOT_SUPPLIED',complete_provider_query:true,record_count:count,
      coverage:'Synthetic test geometry; source coverage unknown',area_metrics:'NOT_USED_UNITS_UNVERIFIED',interpretation:'Current flood state unknown'},chunks,areas:{},geometry_available:true,compressed_bytes:0};
  for(let start=0;start<count;start+=100){
    const rows:FloodFeature[]=Array.from({length:Math.min(100,count-start)},(_,i)=>({type:'Feature',id:createHash('sha256').update(String(start+i)).digest('hex'),properties:null,area_ids:[province,district],geometry:{type:'Polygon',coordinates:[[[100.5,13.7],[100.51,13.7],[100.51,13.71],[100.5,13.7]]]}}));
    const raw=Buffer.from(JSON.stringify(rows)),packed=gzipSync(raw),hash=createHash('sha256').update(raw).digest('hex');
    chunks.push({hash,count:rows.length,raw_bytes:raw.length,compressed_bytes:packed.length,area_ids:['TH',region,province,district]});objects[hash]=packed.toString('base64');manifest.compressed_bytes+=packed.length;
  }
  if(count)for(const id of ['TH',region,province,district])manifest.areas[id]={count,chunks:chunks.map((_,i)=>i)};
  return {manifest,objects,local:{manifests:[manifest],objects}};
}
beforeEach(()=>{vi.clearAllMocks();mocks.uri=null;process.env.HAZARD_LOCAL_SNAPSHOT='1';});
describe('Large GISTDA products and truthful area presentation',()=>{
  it('reads binary doubles exactly and rejects truncated or mixed-codec objects',()=>{
    const {manifest,objects}=fixture(1),original=manifest.chunks[0];
    const rows=decodedFloodObject({payload:Buffer.from(objects[original.hash],'base64'),raw_bytes:original.raw_bytes,compressed_bytes:original.compressed_bytes},original);
    const coords=rows[0].geometry.coordinates as number[][][];
    coords[0][0]=[100.12345678912345,13.98765432198765];
    const raw=Buffer.from(encode(rows)),packed=gzipSync(raw),hash=createHash('sha256').update(raw).digest('hex');
    const descriptor={...original,hash,raw_bytes:raw.length,compressed_bytes:packed.length},object={payload:packed,raw_bytes:raw.length,compressed_bytes:packed.length};
    expect(decodedFloodObject(object,descriptor,'msgpack-gzip-v1')).toEqual(rows);
    expect(()=>decodedFloodObject(object,descriptor,'gzip-v1')).toThrow();
    expect(()=>decodedFloodObject({...object,payload:packed.subarray(0,packed.length-4)},descriptor,'msgpack-gzip-v1')).toThrow();
  });
  it('accepts independent historical metadata and rejects substituted dates/units/provenance',()=>{
    const {manifest}=fixture(25001);
    expect(checkedWindowManifest(manifest).feed.record_count).toBe(25001);
    expect(()=>checkedWindowFeed({...manifest.feed,observed_at:manifest.feed.fetched_at})).toThrow();
    expect(()=>checkedWindowFeed({...manifest.feed,source_url:manifest.feed.source_url.replace('30days','3days')})).toThrow();
    expect(()=>checkedWindowManifest({...manifest,areas:{}})).toThrow();
  });
  it('checks compressed bytes, decompression limits and identity before geometry reaches the browser',()=>{
    const {manifest,objects}=fixture(2),c=manifest.chunks[0],packed=Buffer.from(objects[c.hash],'base64');
    const object={payload:packed,compressed_bytes:packed.length,raw_bytes:c.raw_bytes};
    expect(decodedFloodObject(object,c)).toHaveLength(2);
    expect(()=>decodedFloodObject({...object,payload:packed.subarray(0,30)},c)).toThrow();
    expect(()=>decodedFloodObject(object,{...c,hash:'0'.repeat(64)})).toThrow();
    const bomb=gzipSync(Buffer.alloc(1048577));
    expect(()=>decodedFloodObject({payload:bomb,compressed_bytes:bomb.length,raw_bytes:100},{...c,compressed_bytes:bomb.length,raw_bytes:100})).toThrow();
  });
  it('uses country/province counts for a large response without reading object geometry',async()=>{
    const {local}=fixture(2501);local.objects={};mocks.readFile.mockResolvedValue(JSON.stringify(local));
    const value=await readWindowSnapshot('30days',areaById.get('TH')!,'detail');
    expect(value?.presentation).toBe('summary');expect(value?.records).toEqual([]);
    expect(value?.child_areas).toEqual([{area_id:'TH-P-10',record_count:2501}]);
    expect(value?.feed?.observed_at).toBeNull();expect(value?.scope?.record_count).toBe(2501);
  });
  it('loads all of a small selected area within a pinned generation',async()=>{
    const {local}=fixture(201);mocks.readFile.mockResolvedValue(JSON.stringify(local));const calls:string[]=[];
    const fetcher=(async(url:string)=>{calls.push(url);const p=new URL(url,'http://test').searchParams;return {ok:true,json:()=>readWindowSnapshot('30days',areaById.get('TH-D-1001')!,'detail',Number(p.get('chunk')??0),p.get('generation')??undefined)};}) as typeof fetch;
    const value=await loadFloodSnapshot(new AbortController().signal,fetcher,undefined,{areaId:'TH-D-1001',mode:'detail',window:'30days'});
    expect(calls).toHaveLength(3);expect(value.records).toHaveLength(201);expect(value.pagination?.complete).toBe(true);
  });
  it('loads only the requested 100-feature page of a large district, with an explicit partial state',async()=>{
    const {local}=fixture(2501);mocks.readFile.mockResolvedValue(JSON.stringify(local));const calls:string[]=[];
    const fetcher=(async(url:string)=>{calls.push(url);const p=new URL(url,'http://test').searchParams;return {ok:true,json:()=>readWindowSnapshot('30days',areaById.get('TH-D-1001')!,'detail',Number(p.get('chunk')??0),p.get('generation')??undefined)};}) as typeof fetch;
    const value=await loadFloodSnapshot(new AbortController().signal,fetcher,undefined,{areaId:'TH-D-1001',mode:'detail',window:'30days',page:3});
    expect(calls).toHaveLength(2);expect(value.records).toHaveLength(100);expect(value.scope?.record_count).toBe(2501);
    expect(value.pagination?.chunk).toBe(3);expect(value.presentation).toBe('page');expect(value.pagination?.complete).toBe(false);
  });
  it('keeps archived query clocks distinct and exposes evicted geometry as metadata only',async()=>{
    const {manifest,objects}=fixture(3,'3days');const archived=structuredClone(manifest);archived._id='22222222-2222-4222-8222-222222222222';archived.geometry_available=false;
    archived.feed.fetched_at='2026-11-01T12:00:00Z';archived.feed.response_at=archived.feed.fetched_at;
    mocks.readFile.mockResolvedValue(JSON.stringify({manifests:[manifest,archived],objects}));
    const result=await readWindowSnapshot('3days',areaById.get('TH')!,'detail',0,archived._id);
    expect(result?.historical_query).toBe(true);expect(result?.presentation).toBe('metadata_only');expect(result?.records).toEqual([]);
    expect(result?.feed?.fetched_at).toBe('2026-11-01T12:00:00Z');expect(result?.feed?.observed_at).toBeNull();
  });
  it('rejects a generation change during multi-page assembly',async()=>{
    const {local}=fixture(101);mocks.readFile.mockResolvedValue(JSON.stringify(local));
    const fetcher=(async(url:string)=>{const p=new URL(url,'http://test').searchParams;const value=await readWindowSnapshot('30days',areaById.get('TH-D-1001')!,'detail',Number(p.get('chunk')??0),p.get('generation')??undefined);
      if(p.has('chunk'))value!.pagination!.generation='different-generation';return {ok:true,json:async()=>value};}) as typeof fetch;
    await expect(loadFloodSnapshot(new AbortController().signal,fetcher,undefined,{areaId:'TH-D-1001',mode:'detail',window:'30days'})).rejects.toThrow('changed');
  });
  it('never reuses a cached historical generation for another product window',async()=>{
    const {manifest,objects}=fixture(3);mocks.uri='mongodb://fixture-only';
    const pointer={storage_version:'gzip-v1',active_generation:manifest._id,feature_count:3,record_count:1};
    const cursor=(rows:unknown[])=>({sort:()=>({limit:()=>({toArray:async()=>rows})}),toArray:async()=>rows});
    mocks.database.mockResolvedValue({collection:(name:string)=>({
      findOne:async(q:Record<string,unknown>)=>name==='snapshot_control'?pointer:name==='source_status'?{status:'SUCCESS'}:
        name==='gistda_flood_manifests'?q.product_window&&q.product_window!=='30days'?null:manifest:
        name==='gistda_flood_objects'?{payload:Buffer.from(objects[String(q._id)],'base64'),raw_bytes:manifest.chunks[0].raw_bytes,compressed_bytes:manifest.chunks[0].compressed_bytes}:null,
      find:()=>cursor(name==='snapshot_control'?[pointer]:name==='gistda_flood_manifests'?[manifest]:[])
    })});
    const first=await readWindowSnapshot('30days',areaById.get('TH')!,'detail');expect(first?.records).toHaveLength(3);
    const invalid=await readWindowSnapshot('7days',areaById.get('TH')!,'detail',0,manifest._id);
    expect(invalid?.feed).toBeNull();expect(invalid?.error).toBeTruthy();
  });
});
