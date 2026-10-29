import type {FloodSnapshot} from './types';

/** Assemble one complete generation before it can reach the map. */
export async function loadFloodSnapshot(signal:AbortSignal,fetcher:typeof fetch=fetch,previous?:FloodSnapshot):Promise<FloodSnapshot>{
  let result:FloodSnapshot|null=null,chunk=0,generation:string|undefined;
  const records:FloodSnapshot['records']=[],ids=new Set<string>();
  for(let page=0;page<512;page++){
    const query=chunk?`?chunk=${chunk}&generation=${encodeURIComponent(generation!)}`:'';
    const response=await fetcher('/api/flood-products'+query,{cache:'no-store',signal});
    if(!response.ok)throw new Error('GISTDA page failed');
    const value=await response.json() as FloodSnapshot;
    if(!value.feed){if(page===0&&!value.error)return value;throw new Error('GISTDA generation unavailable');}
    if(value.feed.product_window!=='3days'||value.feed.product_id!=='flood_3days_thailand')throw new Error('Unexpected GISTDA product');
    const pagination=value.pagination;
    if(!pagination||pagination.chunk!==chunk||!Number.isInteger(pagination.chunk_count)||pagination.chunk_count<1||pagination.chunk_count>512||
      (result&&(pagination.generation!==generation||JSON.stringify(value.feed)!==JSON.stringify(result.feed)||pagination.chunk_count!==result.pagination!.chunk_count)))throw new Error('GISTDA generation changed');
    if(page===0&&previous?.pagination?.complete&&previous.pagination.generation===pagination.generation&&
      previous.records.length===value.feed.record_count&&JSON.stringify(previous.feed)===JSON.stringify(value.feed))return {...previous,health:value.health,query_freshness:value.query_freshness};
    if(!Array.isArray(value.records)||value.records.length>100)throw new Error('Invalid GISTDA page');
    for(const row of value.records){
      if(ids.has(row.id)||records.length>=20000)throw new Error('Duplicate or oversized GISTDA generation');
      ids.add(row.id);records.push(row);
    }
    result??=value;generation=pagination.generation;
    if(pagination.next_chunk===null){
      if(chunk!==pagination.chunk_count-1||records.length!==value.feed.record_count)throw new Error('Incomplete GISTDA generation');
      return {feed:result.feed,health:result.health,freshness:result.freshness,query_freshness:result.query_freshness,
        storage:result.storage,error:null,records,pagination:{...pagination,complete:true}};
    }
    if(pagination.next_chunk!==chunk+1||pagination.next_chunk>=pagination.chunk_count)throw new Error('Invalid GISTDA cursor');
    chunk=pagination.next_chunk;
  }
  throw new Error('GISTDA page budget exceeded');
}
