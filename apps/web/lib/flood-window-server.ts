import 'server-only';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
import {Binary} from 'mongodb';
import {decode} from '@msgpack/msgpack';
import {mongoDatabase,mongoUri} from './mongo';
import {areaById,areas} from './geography';
import {floodQueryFreshness} from './floods';
import {checkedWindowManifest,checkedWindowRows,floodBrowserLimit,floodWindows,floodStorageVersions,type FloodStorageVersion,type FloodDescriptor,type FloodManifest} from './flood-window-contract';
import type {Area,FloodSnapshot,FloodWindow} from './types';
import {boundsIntersect,unionBounds,validFloodBounds,floodFeatureBounds,viewportFeatureLimit,viewportByteLimit,type FloodBounds,type FloodViewport} from './flood-viewport';

export function decodedFloodObject(value:unknown,descriptor:FloodDescriptor,version:FloodStorageVersion='gzip-v1'){
  const row=value as {payload?:unknown;compressed_bytes?:number;raw_bytes?:number};
  const bytes=row?.payload instanceof Binary?Buffer.from(row.payload.value()):Buffer.isBuffer(row?.payload)?row.payload:null;
  if(!bytes||bytes.length!==descriptor.compressed_bytes||row.raw_bytes!==descriptor.raw_bytes||row.compressed_bytes!==descriptor.compressed_bytes)throw Error('Invalid compressed flood object');
  const raw=gunzipSync(bytes,{maxOutputLength:1048576});
  if(raw.length!==descriptor.raw_bytes||createHash('sha256').update(raw).digest('hex')!==descriptor.hash)throw Error('Flood object identity mismatch');
  if(!floodStorageVersions.includes(version))throw Error('Unsupported flood encoding');
  const rows=version==='gzip-v1'?JSON.parse(raw.toString('utf8')):decode(raw,{maxStrLength:256,maxBinLength:0,maxExtLength:0,maxArrayLength:131072,maxMapLength:8});
  return checkedWindowRows(rows,descriptor);
}

const spatialCache=new Map<string,{until:number;boxes:FloodBounds[];charge:number}>();let spatialCacheBytes=0;
export function decodedSpatialObject(value:unknown,c:FloodDescriptor):FloodBounds[]{
  const row=value as {payload?:unknown;hash?:string;raw_bytes?:number;compressed_bytes?:number};
  const bytes=row?.payload instanceof Binary?Buffer.from(row.payload.value()):Buffer.isBuffer(row?.payload)?row.payload:null;
  if(!bytes||row.hash!==c.spatial_hash||row.raw_bytes!==c.spatial_raw_bytes||row.compressed_bytes!==c.spatial_compressed_bytes||bytes.length!==c.spatial_compressed_bytes)throw Error('Invalid spatial object');
  const raw=gunzipSync(bytes,{maxOutputLength:8192});
  if(raw.length!==c.spatial_raw_bytes||createHash('sha256').update(raw).digest('hex')!==c.spatial_hash)throw Error('Spatial identity mismatch');
  const boxes=decode(raw,{maxArrayLength:100,maxMapLength:0,maxStrLength:0,maxBinLength:0,maxExtLength:0}) as FloodBounds[];
  if(!Array.isArray(boxes)||boxes.length!==c.count||boxes.some(b=>!validFloodBounds(b))||JSON.stringify(unionBounds(boxes))!==JSON.stringify(c.bbox))throw Error('Spatial accounting mismatch');
  return boxes;
}
export async function readFloodViewport(window:FloodWindow,area:Area,bbox:FloodBounds,generation:string):Promise<FloodViewport>{
  type LocalData={manifests:FloodManifest[];objects:Record<string,string>;spatial_objects?:Record<string,{payload:string;hash:string;raw_bytes:number;compressed_bytes:number}>};
  let manifest:FloodManifest,local:LocalData|null=null;
  if(mongoUri()){
    const hit=manifestCache.get(generation);
    if(hit&&hit.until>Date.now())manifest=hit.value;
    else{
      const db=await mongoDatabase(),row=await db.collection('gistda_flood_manifests').findOne({_id:generation as never,product_window:window,state:'PUBLISHED'},{maxTimeMS:5000});
      manifest=checkedWindowManifest(row);if(manifestCache.size>=12)manifestCache.clear();manifestCache.set(generation,{until:Date.now()+30000,value:manifest});
    }
  }else if(process.env.NODE_ENV!=='production'&&process.env.HAZARD_LOCAL_SNAPSHOT==='1'){
    local=JSON.parse(await readFile(path.join(process.cwd(),'data/local/flood-windows.json'),'utf8'));
    manifest=checkedWindowManifest(local!.manifests.find((m:FloodManifest)=>m._id===generation&&m.product_window===window));
  }else throw Error('Flood storage unavailable');
  if(manifest.product_window!==window||manifest._id!==generation)throw Error('Cross-window generation');
  const result:FloodViewport={generation,window,area_id:area.id,bbox,fetched_at:manifest.feed.fetched_at,source_record_count:manifest.feed.record_count,
    status:'EMPTY',records:[],matched_count:null,complete:false,reason:'',index_chunks:0,geometry_chunks:0};
  if(!manifest.geometry_available)return {...result,status:'GEOMETRY_UNAVAILABLE'};
  if(manifest.spatial_index_version!==1)return {...result,status:'INDEX_UNAVAILABLE'};
  if(bbox[2]-bbox[0]>4||bbox[3]-bbox[1]>4)return {...result,status:'ZOOM_REQUIRED',reason:'VIEW_TOO_WIDE'};
  const candidates=(manifest.areas[area.id]?.chunks??[]).map(i=>manifest.chunks[i]).filter(c=>boundsIntersect(c.bbox!,bbox));
  if(candidates.length>512)return {...result,status:'ZOOM_REQUIRED',reason:'INDEX_SCAN_LIMIT'};
  result.index_chunks=candidates.length;
  const boxes=new Map<string,FloodBounds[]>(),missing:FloodDescriptor[]=[];
  for(const c of candidates){const cached=spatialCache.get(c.hash+':'+c.spatial_hash);if(cached&&cached.until>Date.now())boxes.set(c.hash,cached.boxes);else missing.push(c);}
  const byHash=new Map(missing.map(c=>[c.hash,c]));
  const remember=(row:Record<string,unknown>)=>{
    const c=byHash.get(String(row._id));if(!c)throw Error('Unexpected spatial object');
    const data=decodedSpatialObject(row,c),charge=c.count*128+512,key=c.hash+':'+c.spatial_hash;
    while(spatialCacheBytes+charge>8*1024*1024&&spatialCache.size){const first=spatialCache.keys().next().value!;spatialCacheBytes-=spatialCache.get(first)!.charge;spatialCache.delete(first);}
    const prior=spatialCache.get(key);if(prior)spatialCacheBytes-=prior.charge;
    spatialCache.set(key,{until:Date.now()+300000,boxes:data,charge});spatialCacheBytes+=charge;boxes.set(c.hash,data);
  };
  const db=local?null:await mongoDatabase();
  if(local){for(const c of missing){const row=local.spatial_objects?.[c.hash];if(row)remember({...row,_id:c.hash,payload:Buffer.from(row.payload,'base64')});}}
  else if(missing.length){for await(const row of db!.collection('gistda_flood_spatial').find({_id:{$in:missing.map(c=>c.hash) as never}},{maxTimeMS:5000}).batchSize(64))remember(row);}
  if(boxes.size!==candidates.length)throw Error('Incomplete spatial index');
  const matches=new Map<string,Set<number>>();let total=0;
  for(const c of candidates){const selected=new Set<number>();boxes.get(c.hash)!.forEach((b,i)=>{if(boundsIntersect(b,bbox))selected.add(i);});if(selected.size){matches.set(c.hash,selected);total+=selected.size;}}
  result.matched_count=total;
  const ids=[...matches.keys()].sort().slice(0,64),descriptors=new Map(candidates.map(c=>[c.hash,c]));
  let bytes=2;const unique=new Set<string>();let stopped=false;
  const consume=(row:Record<string,unknown>)=>{
    const c=descriptors.get(String(row._id));if(!c||!matches.has(c.hash))throw Error('Unexpected geometry object');
    const rows=decodedFloodObject(row,c,manifest.storage_version);result.geometry_chunks++;
    for(const index of matches.get(c.hash)!){
      const feature=rows[index];
      if(JSON.stringify(floodFeatureBounds(feature))!==JSON.stringify(boxes.get(c.hash)![index]))throw Error('Geometry differs from spatial index');
      const length=Buffer.byteLength(JSON.stringify(feature))+1;
      if(result.records.length>=viewportFeatureLimit||bytes+length>viewportByteLimit){stopped=true;break;}
      if(unique.has(feature.id))throw Error('Duplicate viewport record');unique.add(feature.id);bytes+=length;result.records.push(feature);
    }
  };
  if(local){for(const id of ids){const c=descriptors.get(id)!,value=local.objects[id];if(!value)throw Error('Missing geometry');consume({_id:id,payload:Buffer.from(value,'base64'),raw_bytes:c.raw_bytes,compressed_bytes:c.compressed_bytes});if(stopped)break;}}
  else if(ids.length){const cursor=db!.collection('gistda_flood_objects').find({_id:{$in:ids as never}},{maxTimeMS:10000}).sort({_id:1}).batchSize(4);try{for await(const row of cursor){consume(row);if(stopped)break;}}finally{await cursor.close();}}
  if(!stopped&&result.geometry_chunks!==ids.length)throw Error('Missing viewport geometry');
  result.complete=result.records.length===total;result.status=result.complete?(total?'AVAILABLE':'EMPTY'):'PARTIAL';
  result.reason=result.complete?'BBOX_INTERSECTIONS_ORIGINAL_GEOMETRY':'BOUNDED_DISPLAY_LIMIT';
  return result;
}
const healthKeys=['status','last_attempt','last_success','completed_at','record_count','provider_number_matched','completeness','scope_area_id','error_summary','failure_stage',
  'last_failure_at','last_failure_reason','last_nonempty_query_at','last_nonempty_count','consecutive_empty_queries','run_url','compressed_bytes','archive_evicted_count'];
function empty():FloodSnapshot{return {feed:null,records:[],health:null,freshness:'UNAVAILABLE',query_freshness:'UNAVAILABLE',storage:mongoUri()?'mongo':'unconfigured',error:null};}
let catalogCache:{until:number;value:NonNullable<FloodSnapshot['window_catalog']>}|null=null;
const manifestCache=new Map<string,{until:number;value:FloodManifest}>();
async function catalog(){
  if(catalogCache&&catalogCache.until>Date.now())return catalogCache.value;
  const db=await mongoDatabase(),pointers=await db.collection('snapshot_control').find({_id:{$in:floodWindows.map(w=>'gistda:flood_'+w+'_thailand') as never}}).toArray();
  const entries=await Promise.all(pointers.filter(p=>floodStorageVersions.includes(p.storage_version)).map(async pointer=>{
    const m=await db.collection('gistda_flood_manifests').findOne({_id:pointer.active_generation},{projection:{product_window:1,'feed.record_count':1,'feed.fetched_at':1,geometry_available:1},maxTimeMS:5000});
    return !m||!floodWindows.includes(m.product_window)||!Number.isInteger(m.feed?.record_count)||m.feed.record_count!==pointer.feature_count?null:
      {window:m.product_window as FloodWindow,record_count:m.feed.record_count as number,fetched_at:m.feed.fetched_at as string,generation:String(m._id),status:'AVAILABLE',geometry_available:m.geometry_available===true};
  }));
  const value=entries.filter((entry):entry is NonNullable<typeof entry>=>entry!==null);
  catalogCache={until:Date.now()+30000,value};return value;
}
export async function readFloodWindowCatalog(){if(!mongoUri())return [];try{return await catalog();}catch{return [];}}
function children(area:Area,m:FloodManifest){
  const level=area.id==='TH'||area.level==='region'?'province':area.level==='province'?'district':null;
  return level?areas.filter(a=>a.level===level&&(area.id==='TH'||area.level==='region'&&a.region_id===area.id||area.level==='province'&&a.province_id===area.id))
    .map(a=>({area_id:a.id,record_count:m.areas[a.id]?.count??0})).filter(a=>a.record_count>0).sort((a,b)=>b.record_count-a.record_count):[];
}
export async function readWindowSnapshot(window:FloodWindow,area:Area,mode:'summary'|'detail',chunk=0,generation?:string):Promise<FloodSnapshot|null>{
  let result=empty();
  try{
    let manifest:FloodManifest,activeGeneration:string|undefined,health:Record<string,unknown>|null=null;
    let history:NonNullable<FloodSnapshot['query_history']>=[],windows:NonNullable<FloodSnapshot['window_catalog']>=[],recent:NonNullable<FloodSnapshot['recent_runs']>=[];
    let object:(descriptor:FloodDescriptor)=>Promise<unknown>;
    if(mongoUri()){
      const db=await mongoDatabase(),key='gistda:flood_'+window+'_thailand';
      const [pointer,status]=await Promise.all([db.collection('snapshot_control').findOne({_id:key as never},{maxTimeMS:5000}),db.collection('source_status').findOne({_id:key as never},{maxTimeMS:5000})]);
      if(!pointer||!floodStorageVersions.includes(pointer.storage_version))return window==='3days'?null:{...result,health:status?Object.fromEntries(healthKeys.map(k=>[k,status[k]??null])):null,window_catalog:await catalog()};
      result.storage='mongo';activeGeneration=pointer.active_generation;
      const id=generation??activeGeneration!;
      if(!/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(id))throw Error('Invalid flood generation');
      const cached=manifestCache.get(id);
      if(cached&&cached.until>Date.now()){
        if(cached.value.product_window!==window)throw Error('Flood generation belongs to another product window');
        manifest=cached.value;
      }
      else{
        const row=await db.collection('gistda_flood_manifests').findOne({_id:id as never,product_window:window},{maxTimeMS:5000});
        if(!row||id!==activeGeneration&&row.state!=='PUBLISHED')throw Error('Flood query history unavailable');
        manifest=checkedWindowManifest(row);
        if(manifestCache.size>=12)manifestCache.clear();manifestCache.set(id,{until:Date.now()+30000,value:manifest});
      }
      if(id===activeGeneration&&(pointer.feature_count!==manifest.feed.record_count||pointer.record_count!==manifest.chunks.length))throw Error('Incomplete flood pointer');
      if(status)health=Object.fromEntries(healthKeys.map(k=>[k,status[k]??null]));
      const [rows,runs,windowsValue]=await Promise.all([
        db.collection('gistda_flood_manifests').find({product_window:window,state:'PUBLISHED',replaced_by:{$exists:false}},{projection:{'feed.fetched_at':1,'feed.record_count':1,geometry_available:1},maxTimeMS:5000}).sort('feed.fetched_at',-1).limit(33).toArray(),
        db.collection('gistda_flood_runs').find({product_id:'flood_'+window+'_thailand'},{projection:{_id:0,status:1,completed_at:1,record_count:1,provider_number_matched:1,error_summary:1,run_url:1},maxTimeMS:5000}).sort('completed_at',-1).limit(5).toArray(),
        catalog()]);
      history=rows.map(row=>({generation:String(row._id),fetched_at:row.feed.fetched_at,record_count:row.feed.record_count,geometry_available:row.geometry_available===true}));
      recent=runs as unknown as typeof recent;windows=windowsValue;
      object=c=>db.collection('gistda_flood_objects').findOne({_id:c.hash as never},{maxTimeMS:5000});
    }else if(process.env.NODE_ENV!=='production'&&process.env.HAZARD_LOCAL_SNAPSHOT==='1'){
      try{
        const local=JSON.parse(await readFile(path.join(process.cwd(),'data/local/flood-windows.json'),'utf8'));
        const active=local.manifests.find((m:FloodManifest)=>m.product_window===window);
        const selected=generation?local.manifests.find((m:FloodManifest)=>m.product_window===window&&m._id===generation):active;
        if(!selected)return window==='3days'?null:result;
        manifest=checkedWindowManifest(selected);activeGeneration=active?._id;result.storage='local';health=local.health?.[window]??{status:'SUCCESS'};
        windows=floodWindows.flatMap(w=>{const m=local.manifests.find((m:FloodManifest)=>m.product_window===w);return m?[{window:m.product_window,record_count:m.feed.record_count,fetched_at:m.feed.fetched_at,generation:m._id,status:'AVAILABLE',geometry_available:m.geometry_available}]:[];});
        history=local.manifests.filter((m:FloodManifest)=>m.product_window===window).map((m:FloodManifest)=>({generation:m._id,fetched_at:m.feed.fetched_at,record_count:m.feed.record_count,geometry_available:m.geometry_available}));
        object=async c=>({payload:Buffer.from(local.objects[c.hash],'base64'),raw_bytes:c.raw_bytes,compressed_bytes:c.compressed_bytes});
      }catch(error){if((error as NodeJS.ErrnoException).code==='ENOENT')return window==='3days'?null:result;throw error;}
    }else return window==='3days'?null:result;
    const feed=manifest.feed,entry=manifest.areas[area.id]??{count:0,chunks:[]},large=entry.count>floodBrowserLimit;
    const presentation=!manifest.geometry_available?'metadata_only':mode==='summary'||large&&area.level!=='district'?'summary':large?'page':'all';
    const summary=presentation==='summary'||presentation==='metadata_only',count=summary?1:Math.max(1,entry.chunks.length);
    if(chunk>=count||chunk<0||summary&&chunk!==0)throw Error('Invalid flood page');
    const descriptor=!summary&&entry.chunks.length?manifest.chunks[entry.chunks[chunk]]:null;
    const records=descriptor?decodedFloodObject(await object(descriptor),descriptor,manifest.storage_version):[];
    result={...result,feed,records,health,freshness:'UNKNOWN',query_freshness:floodQueryFreshness(feed,Date.now(),health?.status==='FAILED'),
      scope:{area_id:area.id,record_count:entry.count,mode},presentation,child_areas:children(area,manifest),
      area_counts:Object.fromEntries(Object.entries(manifest.areas).filter(([id])=>id.startsWith('TH-P-')).map(([id,v])=>[id,v.count])),
      window_catalog:windows,query_history:history,recent_runs:recent,historical_query:manifest._id!==activeGeneration,geometry_available:manifest.geometry_available,history_target_days:window==='3days'?30:0,
      pagination:{generation:manifest._id,chunk,chunk_count:count,next_chunk:!summary&&chunk+1<count?chunk+1:null,complete:!summary&&count===1}};
    return result;
  }catch{return {...result,error:'GISTDA product or query history is temporarily unavailable; no incomplete geometry is displayed'};}
}
