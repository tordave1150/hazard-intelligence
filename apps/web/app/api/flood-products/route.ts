import {readFloodSnapshot} from '@/lib/flood-snapshot';
import {readFloodAreaSnapshot} from '@/lib/flood-area-snapshot';
import {floodResponse} from '@/lib/floods';
import {areaById} from '@/lib/geography';
import {invalid} from '@/lib/http';
import {readWindowSnapshot} from '@/lib/flood-window-server';
import type {FloodWindow} from '@/lib/types';
import {NextResponse} from 'next/server';
export const dynamic='force-dynamic';
export const runtime='nodejs';
export async function GET(request:Request){
  const params=new URL(request.url).searchParams;
  if([...params.keys()].some(key=>!['area_id','chunk','generation','view','window'].includes(key))||[...params.keys()].some(key=>params.getAll(key).length!==1))return invalid('Invalid GISTDA query');
  const window=params.get('window')??'3days';if(!['3days','7days','30days'].includes(window))return invalid('Invalid GISTDA window');
  const view=params.get('view');if(view!==null&&!['summary','detail'].includes(view))return invalid('Invalid GISTDA view');
  const chunkText=params.get('chunk')??'0',generation=params.get('generation')??undefined;
  if(!/^(0|[1-9][0-9]{0,3})$/.test(chunkText)||Number(chunkText)>=5000||(Number(chunkText)>0&&!generation)||
    (generation&&!/^(local|[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})$/.test(generation)))return invalid('Invalid GISTDA page');
  const area=areaById.get(params.get('area_id')??'TH');if(!area)return invalid('Unknown area',404);
  if(view==='summary'&&Number(chunkText)!==0)return invalid('Summary has no geometry pages');
  const streamed=await readWindowSnapshot(window as FloodWindow,area,(view??'detail') as 'summary'|'detail',Number(chunkText),generation);
  const snapshot=streamed??(view?await readFloodAreaSnapshot(area,view as 'summary'|'detail',Number(chunkText),generation):await readFloodSnapshot(Number(chunkText),generation));
  return NextResponse.json({...floodResponse(snapshot,area),storage_protocol:'gistda-gzip-v1'},{status:snapshot.error?503:200,headers:{'Cache-Control':'no-store'}});
}
