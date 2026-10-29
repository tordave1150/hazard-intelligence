import {readFloodSnapshot} from '@/lib/flood-snapshot';
import {floodResponse} from '@/lib/floods';
import {areaById} from '@/lib/geography';
import {invalid,json} from '@/lib/http';
export const dynamic='force-dynamic';
export const runtime='nodejs';
export async function GET(request:Request){
  const params=new URL(request.url).searchParams;
  if([...params.keys()].some(key=>!['area_id','chunk','generation'].includes(key))||[...params.keys()].some(key=>params.getAll(key).length!==1))return invalid('Invalid GISTDA query');
  const chunkText=params.get('chunk')??'0',generation=params.get('generation')??undefined;
  if(!/^(0|[1-9][0-9]{0,2})$/.test(chunkText)||Number(chunkText)>=512||(Number(chunkText)>0&&!generation)||
    (generation&&!/^(local|[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})$/.test(generation)))return invalid('Invalid GISTDA page');
  const area=areaById.get(params.get('area_id')??'TH');if(!area)return invalid('Unknown area',404);
  const snapshot=await readFloodSnapshot(Number(chunkText),generation);
  return json(floodResponse(snapshot,area),snapshot.error?503:200);
}
