import {readFloodSnapshot} from '@/lib/flood-snapshot';
import {floodResponse} from '@/lib/floods';
import {areaById} from '@/lib/geography';
import {invalid,json} from '@/lib/http';
export const dynamic='force-dynamic';
export const runtime='nodejs';
export async function GET(request:Request){
  const params=new URL(request.url).searchParams;
  if([...params.keys()].some(key=>key!=='area_id'))return invalid('Invalid GISTDA query');
  const area=areaById.get(params.get('area_id')??'TH');if(!area)return invalid('Unknown area',404);
  return json(floodResponse(await readFloodSnapshot(),area));
}
