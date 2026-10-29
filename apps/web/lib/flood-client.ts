import type {FloodSnapshot} from './types';

/** Load one complete generation with at most four page requests in flight. */
export async function loadFloodSnapshot(signal:AbortSignal,fetcher:typeof fetch=fetch,previous?:FloodSnapshot):Promise<FloodSnapshot>{
  async function read(chunk:number,generation?:string){
    const query=chunk?`?chunk=${chunk}&generation=${encodeURIComponent(generation!)}`:'';
    const response=await fetcher('/api/flood-products'+query,{cache:'no-store',signal});
    if(!response.ok)throw new Error('GISTDA page failed');
    return await response.json() as FloodSnapshot;
  }
  const first=await read(0);
  if(!first.feed){if(!first.error)return first;throw new Error('GISTDA generation unavailable');}
  const pagination=first.pagination,count=pagination?.chunk_count??0;
  if(!pagination||!Number.isInteger(count)||count<1||count>512||!Number.isInteger(first.feed.record_count)||
    first.feed.record_count<0||first.feed.record_count>20000||first.feed.product_window!=='3days'||first.feed.product_id!=='flood_3days_thailand')throw new Error('Invalid GISTDA generation');
  const generation=pagination.generation,metadata=JSON.stringify(first.feed);
  const records:FloodSnapshot['records']=[],ids=new Set<string>();
  function append(value:FloodSnapshot,index:number){
    const page=value.pagination,expectedNext=index+1<count?index+1:null;
    if(!value.feed||!page||page.chunk!==index||page.chunk_count!==count||page.generation!==generation||
      page.next_chunk!==expectedNext||JSON.stringify(value.feed)!==metadata)throw new Error('GISTDA generation changed');
    if(!Array.isArray(value.records)||value.records.length>100)throw new Error('Invalid GISTDA page');
    for(const row of value.records){
      if(ids.has(row.id)||records.length>=20000)throw new Error('Duplicate or oversized GISTDA generation');
      ids.add(row.id);records.push(row);
    }
  }
  append(first,0);
  if(previous?.pagination?.complete&&previous.pagination.generation===generation&&previous.records.length===first.feed.record_count&&
    JSON.stringify(previous.feed)===metadata)return {...previous,health:first.health,query_freshness:first.query_freshness};
  for(let start=1;start<count;start+=4){
    const indices=Array.from({length:Math.min(4,count-start)},(_,offset)=>start+offset);
    const pages=await Promise.all(indices.map(index=>read(index,generation)));
    pages.forEach((page,index)=>append(page,indices[index]));
  }
  if(records.length!==first.feed.record_count)throw new Error('Incomplete GISTDA generation');
  return {feed:first.feed,health:first.health,freshness:first.freshness,query_freshness:first.query_freshness,
    storage:first.storage,error:null,records,pagination:{...pagination,complete:true,next_chunk:null}};
}
