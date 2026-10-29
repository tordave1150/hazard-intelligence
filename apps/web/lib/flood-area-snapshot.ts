import 'server-only';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
import {mongoDatabase,mongoUri} from './mongo';
import {readFloodSnapshot} from './flood-snapshot';
import {floodRecordsInArea} from './floods';
import {buildFloodAreaIndex,type AreaIndex} from './flood-area-index';
import type {Area,FloodSnapshot} from './types';

let cached:{generation:string;index:AreaIndex}|null=null;
let pending:{generation:string;value:Promise<AreaIndex>}|null=null;
async function areaIndex(first:FloodSnapshot):Promise<AreaIndex>{
  const generation=first.pagination!.generation;
  if(cached?.generation===generation)return cached.index;
  if(pending?.generation===generation)return pending.value;
  const value=(async()=>{
    let rows:{chunk_id:string;records:{id:string;area_ids?:string[]}[]}[];
    if(mongoUri()){
      const db=await mongoDatabase();
      // Only IDs and administrative membership cross the database boundary here, never all geometry.
      rows=await db.collection('satellite_flood_3days_latest').find({source_id:'gistda',product_id:'flood_3days_thailand',etl_run_id:generation},
        {projection:{_id:0,chunk_id:1,'records.id':1,'records.area_ids':1},maxTimeMS:5000}).limit(513).toArray() as unknown as typeof rows;
    }else{
      const payload=JSON.parse(await readFile(path.join(process.cwd(),'data/local/floods.json'),'utf8'));
      rows=Array.from({length:first.pagination!.chunk_count},(_,chunk)=>({chunk_id:String(chunk).padStart(4,'0'),records:payload.feed.records.slice(chunk*100,(chunk+1)*100)}));
    }
    const index=buildFloodAreaIndex(rows,first.feed!.record_count,first.pagination!.chunk_count);
    cached={generation,index};return index;
  })();
  pending={generation,value};
  try{return await value;}finally{if(pending?.value===value)pending=null;}
}

export async function readFloodAreaSnapshot(area:Area,mode:'summary'|'detail',chunk=0,generation?:string):Promise<FloodSnapshot>{
  const first=await readFloodSnapshot(0);
  if(!first.feed)return first;
  try{
    if(!first.pagination||generation&&generation!==first.pagination.generation)throw Error('Generation changed');
    const index=await areaIndex(first),entry=index.get(area.id)??{count:0,chunks:[]};
    const count=Math.max(1,entry.chunks.length);
    if(chunk>=count||mode==='summary'&&chunk!==0)throw Error('Invalid scoped chunk');
    const page=mode==='detail'&&entry.chunks.length?
      await readFloodSnapshot(entry.chunks[chunk],first.pagination.generation):first;
    if(page.error||!page.feed||page.pagination?.generation!==first.pagination.generation||JSON.stringify(page.feed)!==JSON.stringify(first.feed))throw Error('Generation changed');
    return {...first,records:mode==='detail'&&entry.chunks.length?floodRecordsInArea(page,area):[],
      scope:{area_id:area.id,record_count:entry.count,mode},pagination:{generation:first.pagination.generation,chunk,
        chunk_count:mode==='summary'?1:count,next_chunk:mode==='detail'&&chunk+1<count?chunk+1:null,
        complete:mode==='detail'&&count===1}};
  }catch{
    return {...first,feed:null,records:[],error:'GISTDA area query is unavailable or its generation changed. Retry the complete area query.',freshness:'UNAVAILABLE',query_freshness:'UNAVAILABLE',pagination:undefined};
  }
}
