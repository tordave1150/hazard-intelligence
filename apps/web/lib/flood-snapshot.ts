import 'server-only';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
import {mongoDatabase,mongoUri} from './mongo';
import {validatedFloodFeed} from './contracts';
import {floodQueryFreshness} from './floods';
import type {FloodFeed,FloodSnapshot} from './types';

let cache:{until:number;value:FloodSnapshot}|null=null;
const key='gistda:flood_1day_ongkharak';
function metadata(feed:FloodFeed|null){if(!feed)return null;const {records,...value}=feed;return value;}
export async function readFloodSnapshot():Promise<FloodSnapshot>{
  if(cache&&cache.until>Date.now())return cache.value;
  let result:FloodSnapshot={feed:null,records:[],health:null,freshness:'UNAVAILABLE',query_freshness:'UNAVAILABLE',storage:'unconfigured',error:null};
  try{
    if(mongoUri()){
      result.storage='mongo';const db=await mongoDatabase();let feed:FloodFeed|null=null;
      for(let attempt=0;attempt<3;attempt++){
        const pointer=await db.collection('snapshot_control').findOne({_id:key as never},{maxTimeMS:5000});
        if(!pointer)break;
        if(pointer.record_count!==1||!['A','B'].includes(pointer.active_slot))throw new Error('Invalid GISTDA pointer');
        const row=await db.collection('satellite_flood_latest').findOne({source_id:'gistda',product_id:'flood_1day_ongkharak',
          snapshot_id:'latest',slot:pointer.active_slot,etl_run_id:pointer.active_run_id},{projection:{_id:0,slot:0,etl_run_id:0},maxTimeMS:5000});
        if(row){feed=validatedFloodFeed(row);break;}
        if(attempt===2)throw new Error('GISTDA pointer changed during query');
      }
      const status=await db.collection('source_status').findOne({_id:key as never},{maxTimeMS:5000});
      const health=status?Object.fromEntries(['status','last_attempt','last_success','completed_at','record_count','completeness','scope_area_id'].map(k=>[k,status[k]??null])):null;
      if(health)health.error_summary=status?.status==='FAILED'?status.error_summary??null:null;
      result={...result,feed:metadata(feed),records:feed?.records??[],health};
    }else if(process.env.NODE_ENV!=='production'&&process.env.HAZARD_LOCAL_SNAPSHOT==='1'){
      const value=JSON.parse(await readFile(path.join(process.cwd(),'data/local/floods.json'),'utf-8'));
      const feed=validatedFloodFeed(value.feed);
      result={...result,feed:metadata(feed),records:feed.records,health:value.status??null,storage:'local'};
    }
  }catch{
    result={feed:null,records:[],health:null,freshness:'UNAVAILABLE',query_freshness:'UNAVAILABLE',storage:mongoUri()?'mongo':'unconfigured',error:'GISTDA district snapshot is temporarily unavailable'};
  }
  // A recently completed query cannot establish the unknown satellite acquisition age.
  result.freshness=result.feed?'UNKNOWN':'UNAVAILABLE';
  result.query_freshness=floodQueryFreshness(result.feed,Date.now(),result.health?.status==='FAILED');
  cache={until:Date.now()+(result.error?10000:60000),value:result};return result;
}
