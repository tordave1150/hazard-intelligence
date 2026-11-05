import type {FloodSnapshot,FloodWindow} from './types';

/** Load one complete generation with at most four page requests in flight. */
export async function loadFloodSnapshot(signal:AbortSignal,fetcher:typeof fetch=fetch,previous?:FloodSnapshot,options?:{areaId:string;mode:'summary'|'detail';window?:FloodWindow;generation?:string;page?:number}):Promise<FloodSnapshot>{
  async function read(chunk:number,generation?:string){
    const params=new URLSearchParams();
    if(chunk){params.set('chunk',String(chunk));params.set('generation',generation!);}
    if(options){params.set('area_id',options.areaId);params.set('view',options.mode);}
    if(options?.window)params.set('window',options.window);
    if(generation??options?.generation)params.set('generation',(generation??options?.generation)!);
    const query=params.size?'?'+params.toString():'';
    const response=await fetcher('/api/flood-products'+query,{cache:'no-store',signal});
    if(!response.ok)throw new Error('GISTDA page failed');
    return await response.json() as FloodSnapshot;
  }
  const first=await read(0);
  if(!first.feed){if(!first.error)return first;throw new Error('GISTDA generation unavailable');}
  if(first.feed.schema_version==='3.0')return loadWindow(first,read,options);
  const pagination=first.pagination,count=pagination?.chunk_count??0;
  if(!pagination||!Number.isInteger(count)||count<1||count>512||!Number.isInteger(first.feed.record_count)||
    first.feed.record_count<0||first.feed.record_count>20000||first.feed.product_window!=='3days'||first.feed.product_id!=='flood_3days_thailand')throw new Error('Invalid GISTDA generation');
  const generation=pagination.generation,metadata=JSON.stringify(first.feed);
  const scope=first.scope,expectedCount=scope?.record_count??first.feed.record_count;
  if(options&&(!scope||scope.area_id!==options.areaId||scope.mode!==options.mode||!Number.isInteger(scope.record_count)||scope.record_count<0||scope.record_count>first.feed.record_count))throw Error('Invalid GISTDA area result');
  if(options?.mode==='summary'){
    if(first.records.length||pagination.complete||pagination.chunk!==0||pagination.chunk_count!==1||pagination.next_chunk!==null)throw Error('Invalid GISTDA summary');
    return first;
  }
  const records:FloodSnapshot['records']=[],ids=new Set<string>();
  function append(value:FloodSnapshot,index:number){
    const page=value.pagination,expectedNext=index+1<count?index+1:null;
    if(!value.feed||!page||page.chunk!==index||page.chunk_count!==count||page.generation!==generation||
      page.next_chunk!==expectedNext||JSON.stringify(value.feed)!==metadata||JSON.stringify(value.scope)!==JSON.stringify(scope))throw new Error('GISTDA generation changed');
    if(!Array.isArray(value.records)||value.records.length>100)throw new Error('Invalid GISTDA page');
    for(const row of value.records){
      if(ids.has(row.id)||records.length>=20000)throw new Error('Duplicate or oversized GISTDA generation');
      ids.add(row.id);records.push(row);
    }
  }
  append(first,0);
  if(previous?.pagination?.complete&&previous.pagination.generation===generation&&previous.records.length===expectedCount&&
    JSON.stringify(previous.feed)===metadata&&JSON.stringify(previous.scope)===JSON.stringify(scope))return {...previous,health:first.health,query_freshness:first.query_freshness};
  for(let start=1;start<count;start+=4){
    const indices=Array.from({length:Math.min(4,count-start)},(_,offset)=>start+offset);
    const pages=await Promise.all(indices.map(index=>read(index,generation)));
    pages.forEach((page,index)=>append(page,indices[index]));
  }
  if(records.length!==expectedCount)throw new Error('Incomplete GISTDA generation');
  return {feed:first.feed,health:first.health,freshness:first.freshness,query_freshness:first.query_freshness,
    storage:first.storage,error:null,records,...(scope?{scope}:{}),pagination:{...pagination,complete:true,next_chunk:null}};
}

async function loadWindow(first:FloodSnapshot,read:(chunk:number,generation?:string)=>Promise<FloodSnapshot>,options?:{areaId:string;mode:'summary'|'detail';window?:FloodWindow;page?:number}){
  const feed=first.feed!,pagination=first.pagination,scope=first.scope,window=options?.window??'3days';
  if(!pagination||!scope||scope.area_id!==(options?.areaId??'TH')||scope.mode!==(options?.mode??'detail')||feed.product_window!==window||feed.product_id!=='flood_'+window+'_thailand'||
    !Number.isInteger(feed.record_count)||feed.record_count<0||feed.record_count>250000||!Number.isInteger(scope.record_count)||scope.record_count<0||scope.record_count>feed.record_count||
    !Number.isInteger(pagination.chunk_count)||pagination.chunk_count<1||pagination.chunk_count>5000)throw Error('Invalid compressed flood response');
  if(first.presentation==='summary'||first.presentation==='metadata_only'){
    if(first.records.length||pagination.complete||pagination.chunk_count!==1||pagination.next_chunk!==null)throw Error('Invalid flood summary');
    return first;
  }
  const metadata=JSON.stringify(feed),membership=JSON.stringify(scope),records:FloodSnapshot['records']=[],ids=new Set<string>();
  function checked(page:FloodSnapshot,index:number){
    const p=page.pagination;
    if(!p||p.generation!==pagination!.generation||p.chunk!==index||p.chunk_count!==pagination!.chunk_count||p.next_chunk!==(index+1<p.chunk_count?index+1:null)||
      JSON.stringify(page.feed)!==metadata||JSON.stringify(page.scope)!==membership||!Array.isArray(page.records)||page.records.length>100)throw Error('Flood query changed while loading');
    for(const row of page.records){if(ids.has(row.id))throw Error('Repeated flood feature');ids.add(row.id);records.push(row);}
  }
  if(first.presentation==='page'){
    const index=Math.min(Math.max(0,options?.page??0),pagination.chunk_count-1);
    const page=index?await read(index,pagination.generation):first;checked(page,index);return page;
  }
  if(first.presentation!=='all'||scope.record_count>2000||pagination.chunk_count>2000)throw Error('Flood browser geometry budget exceeded');
  checked(first,0);
  for(let start=1;start<pagination.chunk_count;start+=4){
    const indices=Array.from({length:Math.min(4,pagination.chunk_count-start)},(_,i)=>start+i);
    const pages=await Promise.all(indices.map(index=>read(index,pagination.generation)));
    pages.forEach((p,i)=>checked(p,indices[i]));
  }
  if(records.length!==scope.record_count)throw Error('Incomplete flood area query');
  return {...first,records,pagination:{...pagination,complete:true,next_chunk:null}};
}
