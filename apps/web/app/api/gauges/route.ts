import {readGaugeSnapshot} from '@/lib/gauge-snapshot';
import {gaugeResponse} from '@/lib/gauges';
import {readRainSnapshot} from '@/lib/rain-snapshot';
import {rainResponse} from '@/lib/rain-gauges';
import {areaById} from '@/lib/geography';
import {invalid,json} from '@/lib/http';
export const dynamic='force-dynamic';
export const runtime='nodejs';
export async function GET(request:Request){
  const params=new URL(request.url).searchParams;
  if([...params.keys()].some(k=>!['area_id','kind','view'].includes(k)||params.getAll(k).length!==1))return invalid('Invalid station query');
  const area=areaById.get(params.get('area_id')??'TH');if(!area)return invalid('Unsupported station area',404);
  const kind=params.get('kind')??'river';if(!['river','rain'].includes(kind))return invalid('Invalid gauge kind');
  const view=params.get('view')??'detail';if(!['summary','detail'].includes(view)||kind==='river'&&params.has('view'))return invalid('Invalid station view');
  if(kind==='rain'){const snapshot=await readRainSnapshot();return json(rainResponse(snapshot,area,view==='summary'),snapshot.error?503:200);}
  const snapshot=await readGaugeSnapshot();
  return json(gaugeResponse(snapshot,area),snapshot.error&&kind==='river'?503:200);
}
