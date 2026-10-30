import {readGaugeSnapshot} from '@/lib/gauge-snapshot';
import {readGaugeHistory} from '@/lib/gauge-history';
import {invalid,json} from '@/lib/http';
export const dynamic='force-dynamic';
export const runtime='nodejs';
export const maxDuration=30;
export async function GET(request:Request){
  const params=new URL(request.url).searchParams,id=params.get('gauge_id');
  if([...params.keys()].some(k=>k!=='gauge_id'||params.getAll(k).length!==1)||!id||!/^THW-[0-9]{1,12}$/.test(id))return invalid('Invalid station history query');
  const snapshot=await readGaugeSnapshot();
  if(!snapshot.feed)return invalid('Published station response is unavailable',503);
  const station=snapshot.records.find(row=>row.gauge_id===id);if(!station)return invalid('Unknown published station',404);
  try{return json(await readGaugeHistory(station));}
  catch{return invalid('Station history is unavailable; the latest station observation remains visible',503);}
}
