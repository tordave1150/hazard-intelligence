import Ajv from 'ajv/dist/2020';
import addFormats from 'ajv-formats';
import schema from '../../../packages/contracts/flood-window.schema.json';
import {areaById} from './geography';
import type {FloodFeed,FloodFeature,FloodWindow} from './types';
import {validFloodBounds,type FloodBounds} from './flood-viewport';
const ajv=new Ajv({strict:false});addFormats(ajv);ajv.addSchema(schema);
const metadata=ajv.compile({$ref:schema.$id+'#/$defs/Metadata'}),payload=ajv.compile({$ref:schema.$id+'#/$defs/ChunkPayload'});
export const floodWindows:FloodWindow[]=['3days','7days','30days'];
export const floodBrowserLimit=2000;
export const floodStorageVersions=['gzip-v1','msgpack-gzip-v1'] as const;
export type FloodStorageVersion=typeof floodStorageVersions[number];
export type FloodDescriptor={hash:string;count:number;raw_bytes:number;compressed_bytes:number;area_ids:string[];
  bbox?:FloodBounds;spatial_hash?:string;spatial_raw_bytes?:number;spatial_compressed_bytes?:number};
export type FloodManifest={_id:string;storage_version:FloodStorageVersion;product_window:FloodWindow;feed:Omit<FloodFeed,'records'>;
  chunks:FloodDescriptor[];areas:Record<string,{count:number;chunks:number[]}>;geometry_available:boolean;compressed_bytes:number;spatial_index_version?:1};
export function checkedWindowFeed(value:unknown){
  if(!metadata(value))throw Error('Invalid flood window metadata');
  const feed=value as Omit<FloodFeed,'records'>;
  if(feed.product_id!=='flood_'+feed.product_window+'_thailand'||feed.source_url!=='https://api-gateway.gistda.or.th/api/2.0/resources/features/flood/'+feed.product_window||
    Date.parse(feed.response_at)>Date.parse(feed.fetched_at)+300000||Date.parse(feed.fetched_at)>Date.parse(feed.ingested_at))throw Error('Invalid flood provenance or clocks');
  return feed;
}
export function checkedWindowManifest(value:unknown):FloodManifest{
  if(!value||typeof value!=='object')throw Error('Missing flood manifest');
  const m=value as FloodManifest,feed=checkedWindowFeed(m.feed);
  if(m.spatial_index_version!==undefined&&m.spatial_index_version!==1)throw Error('Unsupported flood spatial index');
  if(!floodStorageVersions.includes(m.storage_version)||m.product_window!==feed.product_window||!Array.isArray(m.chunks)||m.chunks.length>5000||!m.areas||typeof m.geometry_available!=='boolean')throw Error('Invalid flood storage contract');
  const rebuilt:typeof m.areas={},hashes=new Set<string>();let count=0,bytes=0;
  for(const [index,c] of m.chunks.entries()){
    if(m.spatial_index_version===1&&(!validFloodBounds(c.bbox)||!/^[a-f0-9]{64}$/.test(c.spatial_hash??'')||
      !Number.isInteger(c.spatial_raw_bytes)||c.spatial_raw_bytes!<1||c.spatial_raw_bytes!>8192||
      !Number.isInteger(c.spatial_compressed_bytes)||c.spatial_compressed_bytes!<1||c.spatial_compressed_bytes!>8192))throw Error('Invalid flood spatial descriptor');
    if(!c||!Array.isArray(c.area_ids)||c.area_ids.length!==4||!/^[a-f0-9]{64}$/.test(c.hash)||hashes.has(c.hash)||!Number.isInteger(c.count)||c.count<1||c.count>100||
      !Number.isInteger(c.raw_bytes)||c.raw_bytes<1||c.raw_bytes>1048576||!Number.isInteger(c.compressed_bytes)||c.compressed_bytes<1||c.compressed_bytes>1048576)throw Error('Invalid flood chunk descriptor');
    const district=areaById.get(c.area_ids[3]),province=district?.province_id?areaById.get(district.province_id):undefined;
    if(district?.level!=='district'||!province||JSON.stringify(c.area_ids)!==JSON.stringify(['TH',province.region_id,province.id,district.id]))throw Error('Invalid flood administrative index');
    for(const id of c.area_ids){const entry=rebuilt[id]??={count:0,chunks:[]};entry.count+=c.count;entry.chunks.push(index);}
    hashes.add(c.hash);count+=c.count;bytes+=c.compressed_bytes;
  }
  if(count!==feed.record_count||bytes!==m.compressed_bytes||Object.keys(rebuilt).length!==Object.keys(m.areas).length||
    Object.entries(rebuilt).some(([id,entry])=>JSON.stringify(entry)!==JSON.stringify(m.areas[id])))throw Error('Incomplete flood index');
  return m;
}
export function checkedWindowRows(value:unknown,descriptor:FloodDescriptor):FloodFeature[]{
  if(!payload(value)||!Array.isArray(value)||value.length!==descriptor.count)throw Error('Invalid flood geometry chunk');
  const rows=value as FloodFeature[],ids=new Set<string>();
  for(const row of rows){if(ids.has(row.id)||JSON.stringify(row.area_ids)!==JSON.stringify(descriptor.area_ids.slice(2)))throw Error('Invalid flood chunk membership');ids.add(row.id);}
  return rows;
}
