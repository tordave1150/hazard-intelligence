import {readGaugeSnapshot} from '@/lib/gauge-snapshot';
import {gaugeResponse} from '@/lib/gauges';
import {areaById} from '@/lib/geography';
import {invalid,json} from '@/lib/http';
export const dynamic='force-dynamic';
export const runtime='nodejs';
export async function GET(request:Request){
  const params=new URL(request.url).searchParams;
  if([...params.keys()].some(k=>!['area_id','kind'].includes(k)||params.getAll(k).length!==1))return invalid('Invalid station query');
  const area=areaById.get(params.get('area_id')??'TH');if(!area||area.level==='basin')return invalid('Unsupported station area',404);
  const kind=params.get('kind')??'river';if(!['river','rain'].includes(kind))return invalid('Invalid gauge kind');
  const snapshot=await readGaugeSnapshot();
  return json(gaugeResponse(snapshot,area,kind),snapshot.error&&kind==='river'?503:200);
}
