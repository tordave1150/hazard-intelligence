import {readSnapshot} from '@/lib/snapshot';
import {areaMembers,areaById} from '@/lib/geography';
import {invalid,json} from '@/lib/http';
export const dynamic='force-dynamic';
export async function GET(request:Request) {
  const q=new URL(request.url).searchParams, id=q.get('area_id')??'TH', date=q.get('valid_date'), metric=q.get('metric');
  if(!areaById.has(id))return invalid('Unknown area',404);
  if(date&&!/^\d{4}-\d{2}-\d{2}$/.test(date))return invalid('Use YYYY-MM-DD');
  if(metric&&!['rainfall_mm','rain_probability_pct'].includes(metric))return invalid('Unsupported metric');
  const ids=new Set(areaMembers(id).map(a=>a.id));
  const snapshot=await readSnapshot();
  return json({...snapshot,records:snapshot.records.filter(r=>ids.has(r.location_id)).map(r=>({...r,
    valid_periods:date?r.valid_periods.filter(p=>p.date===date):r.valid_periods}))});
}
