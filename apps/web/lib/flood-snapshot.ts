import 'server-only';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
import {mongoDatabase,mongoUri} from './mongo';
import {validatedFloodFeed,validatedFloodChunk} from './contracts';
import {floodQueryFreshness} from './floods';
import type {FloodFeed,FloodSnapshot} from './types';

const product='flood_3days_thailand',collection='satellite_flood_3days_latest',key='gistda:'+product;
let cache:{until:number;value:FloodSnapshot}|null=null;
function metadata(feed:FloodFeed){const {records,...value}=feed;return value;}
export async function readFloodSnapshot(chunk=0,generation?:string):Promise<FloodSnapshot>{
  if(chunk===0&&!generation&&cache&&cache.until>Date.now())return cache.value;
  let result:FloodSnapshot={feed:null,records:[],health:null,freshness:'UNAVAILABLE',query_freshness:'UNAVAILABLE',storage:'unconfigured',error:null};
  try{
    if(mongoUri()){
      result.storage='mongo';const db=await mongoDatabase();
      const [pointer,status]=await Promise.all([
        db.collection('snapshot_control').findOne({_id:key as never},{maxTimeMS:5000}),
        db.collection('source_status').findOne({_id:key as never},{maxTimeMS:5000})]);
      const health=status?Object.fromEntries(['status','last_attempt','last_success','completed_at','record_count','completeness','scope_area_id'].map(k=>[k,status[k]??null])):null;
      if(health)health.error_summary=status?.status==='FAILED'?status.error_summary??null:null;
      result.health=health;
      if(pointer){
        if(!Number.isInteger(pointer.record_count)||pointer.record_count<1||pointer.record_count>512||!['A','B'].includes(pointer.active_slot))throw new Error('Invalid GISTDA pointer');
        if(chunk>=pointer.record_count||(generation&&generation!==pointer.active_run_id))throw new Error('GISTDA generation changed');
        const row=await db.collection(collection).findOne({source_id:'gistda',product_id:product,
          chunk_id:String(chunk).padStart(4,'0'),slot:pointer.active_slot,etl_run_id:pointer.active_run_id},
          {projection:{_id:0,slot:0,etl_run_id:0},maxTimeMS:5000});
        const value=validatedFloodChunk(row);
        if(value.chunk_count!==pointer.record_count||value.feed.record_count!==pointer.feature_count)throw new Error('Incomplete GISTDA generation');
        result={...result,feed:value.feed,records:value.records,pagination:{generation:pointer.active_run_id,chunk,
          chunk_count:value.chunk_count,next_chunk:chunk+1<value.chunk_count?chunk+1:null,complete:value.chunk_count===1}};
      }
    }else if(process.env.NODE_ENV!=='production'&&process.env.HAZARD_LOCAL_SNAPSHOT==='1'){
      const value=JSON.parse(await readFile(path.join(process.cwd(),'data/local/floods.json'),'utf-8'));
      const feed=validatedFloodFeed(value.feed);
      if(feed.product_window!=='3days')throw new Error('Local GISTDA preview must be three-day');
      const count=Math.max(1,Math.ceil(feed.record_count/100));
      if(chunk>=count||(generation&&generation!=='local'))throw new Error('Invalid local GISTDA page');
      result={...result,feed:metadata(feed),records:feed.records.slice(chunk*100,(chunk+1)*100),health:value.status??null,storage:'local',
        pagination:{generation:'local',chunk,chunk_count:count,next_chunk:chunk+1<count?chunk+1:null,complete:count===1}};
    }
  }catch{
    result={feed:null,records:[],health:null,freshness:'UNAVAILABLE',query_freshness:'UNAVAILABLE',storage:mongoUri()?'mongo':'unconfigured',error:'GISTDA three-day product is unavailable or changed during loading. Retry the complete query.'};
  }
  result.freshness=result.feed?'UNKNOWN':'UNAVAILABLE';
  result.query_freshness=floodQueryFreshness(result.feed,Date.now(),result.health?.status==='FAILED');
  if(chunk===0&&!generation)cache={until:Date.now()+(result.error?10000:60000),value:result};
  return result;
}
