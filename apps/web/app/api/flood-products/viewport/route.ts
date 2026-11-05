import {NextResponse} from 'next/server';
import {areaById} from '@/lib/geography';
import {readFloodViewport} from '@/lib/flood-window-server';
import {validFloodBounds} from '@/lib/flood-viewport';
import type {FloodWindow} from '@/lib/types';
import {invalid} from '@/lib/http';
export const runtime='nodejs';
export const dynamic='force-dynamic';
export const maxDuration=30;
export async function GET(request:Request){
  const params=new URL(request.url).searchParams;
  if([...params.keys()].some(k=>!['window','area_id','generation','bbox'].includes(k)||params.getAll(k).length!==1))return invalid('Invalid viewport query');
  const window=params.get('window'),generation=params.get('generation'),raw=params.get('bbox')??'',area=areaById.get(params.get('area_id')??'TH');
  const parts=raw.split(','),bbox=parts.map(Number);
  if(!window||!['3days','7days','30days'].includes(window)||!generation||!/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(generation)||
    raw.length>100||parts.some(v=>!/^[-]?\d{1,3}(\.\d{1,6})?$/.test(v))||!validFloodBounds(bbox)||bbox[0]===bbox[2]||bbox[1]===bbox[3])return invalid('Invalid pinned viewport');
  if(!area||area.level==='basin')return invalid('Unsupported viewport area');
  try{return NextResponse.json(await readFloodViewport(window as FloodWindow,area,bbox,generation),{headers:{'Cache-Control':'no-store'}});}
  catch{return NextResponse.json({status:'UNAVAILABLE',records:[],complete:false,error:'Selected query or spatial index temporarily unavailable; current flood state unknown'},{status:503,headers:{'Cache-Control':'no-store'}});}
}
