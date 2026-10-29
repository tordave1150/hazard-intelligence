import {areaById} from './geography';

export type AreaIndex=Map<string,{count:number;chunks:number[]}>;
/** Count each footprint once per ancestor; province-only codes never imply a district. */
export function buildFloodAreaIndex(rows:{chunk_id:string;records:{id:string;area_ids?:string[]}[]}[],featureCount:number,chunkCount:number):AreaIndex{
  if(!Number.isInteger(featureCount)||featureCount<0||featureCount>20000||!Number.isInteger(chunkCount)||chunkCount<1||chunkCount>512||rows.length!==chunkCount)throw Error('Invalid flood index size');
  const ids=new Set<string>(),chunks=new Set<number>(),index:AreaIndex=new Map();
  for(const row of rows){
    if(!/^\d{4}$/.test(row.chunk_id))throw Error('Invalid flood index chunk');
    const chunk=Number(row.chunk_id);
    if(chunk>=chunkCount||chunks.has(chunk)||!Array.isArray(row.records)||row.records.length>100)throw Error('Invalid flood index chunk');
    chunks.add(chunk);
    for(const record of row.records){
      if(typeof record.id!=='string'||!record.id||ids.has(record.id)||ids.size>=20000||
        (record.area_ids!==undefined&&(!Array.isArray(record.area_ids)||record.area_ids.length>32)))throw Error('Invalid flood index record');
      ids.add(record.id);
      const members=new Set(['TH']);
      for(const id of record.area_ids??[]){
        let area=areaById.get(id);
        if(!area||!['province','district'].includes(area.level))throw Error('Unknown flood administrative code');
        while(area){members.add(area.id);area=area.parent_id?areaById.get(area.parent_id):undefined;}
      }
      for(const id of members){
        const entry=index.get(id)??{count:0,chunks:[]};entry.count++;
        if(!entry.chunks.includes(chunk))entry.chunks.push(chunk);
        index.set(id,entry);
      }
    }
  }
  if(ids.size!==featureCount)throw Error('Incomplete flood index');
  for(const entry of index.values())entry.chunks.sort((a,b)=>a-b);
  return index;
}
