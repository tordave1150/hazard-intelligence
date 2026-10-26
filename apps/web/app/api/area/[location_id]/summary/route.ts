import {areaById,areaMembers} from '@/lib/geography';
import {readSnapshot} from '@/lib/snapshot';
import {invalid,json} from '@/lib/http';
export const dynamic='force-dynamic';
export async function GET(_request:Request,{params}:{params:Promise<{location_id:string}>}) {
  const {location_id}=await params, area=areaById.get(location_id);
  if(!area)return invalid('Unknown area',404);
  const ids=new Set(areaMembers(location_id).map(a=>a.id)),snapshot=await readSnapshot();
  return json({area,weather:{...snapshot,records:snapshot.records.filter(r=>ids.has(r.location_id))},
    water:{status:'UNAVAILABLE',reason:'Source acceptance pending'},warnings:{status:'UNAVAILABLE'},satellite:{status:'UNAVAILABLE'}});
}
