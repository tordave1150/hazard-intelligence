import {readHourlySnapshot} from '@/lib/hourly-snapshot';
import {areaById} from '@/lib/geography';
import {contains,bangkokDate} from '@/lib/semantics';
import {invalid,json} from '@/lib/http';
export const dynamic='force-dynamic';
export const runtime='nodejs';
export async function GET(request:Request){
  const params=new URL(request.url).searchParams;
  if([...params.keys()].some(key=>!['area_id','valid_end'].includes(key)))return invalid('Invalid hourly query');
  const area=areaById.get(params.get('area_id')??'TH');if(!area||area.level==='basin')return invalid('Unsupported hourly area',404);
  const snapshot=await readHourlySnapshot();
  const current=snapshot.records[0]?.forecast_date===bangkokDate();
  const hours=current?snapshot.records[0].valid_hours.map(h=>({valid_start:h.valid_start,valid_end:h.valid_end})):[];
  const requested=params.get('valid_end');
  if(requested&&!hours.some(h=>h.valid_end===requested))return invalid('Unsupported hourly interval');
  const end=requested??hours.find(h=>Date.parse(h.valid_end)>Date.now())?.valid_end??null;
  return json({...snapshot,view_kind:'single_interval',available_hours:hours,selected_hour_end:end,
    records:snapshot.records.filter(r=>contains(area,areaById.get(r.location_id)!)).map(r=>({...r,valid_hours:r.valid_hours.filter(h=>h.valid_end===end)}))});
}
