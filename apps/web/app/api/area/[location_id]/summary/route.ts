import {areas,areaById,areaMembers} from '@/lib/geography';
import {readSnapshot} from '@/lib/snapshot';
import {readWarningSnapshot} from '@/lib/warning-snapshot';
import {warningInArea,warningState} from '@/lib/warnings';
import {readFloodAreaSnapshot} from '@/lib/flood-area-snapshot';
import {floodResponse} from '@/lib/floods';
import {readGaugeSnapshot} from '@/lib/gauge-snapshot';
import {gaugeResponse} from '@/lib/gauges';
import {invalid,json} from '@/lib/http';
export const dynamic='force-dynamic';
export async function GET(_request:Request,{params}:{params:Promise<{location_id:string}>}) {
  const {location_id}=await params, area=areaById.get(location_id);
  if(!area)return invalid('Unknown area',404);
  const ids=new Set(areaMembers(location_id).map(a=>a.id));
  const [snapshot,warnings,floods,gauges]=await Promise.all([readSnapshot(),readWarningSnapshot(),readFloodAreaSnapshot(area,'summary'),readGaugeSnapshot()]);
  const messages=warnings.records.filter(row=>warningInArea(row,area,areas));
  return json({area,weather:{...snapshot,records:snapshot.records.filter(r=>ids.has(r.location_id))},
    water:gaugeResponse(gauges,area,'river'),
    warnings:{...warnings,records:messages,status:warnings.freshness,current_count:messages.filter(row=>warningState(row,warnings.records)==='CURRENT').length},
    satellite:floodResponse(floods,area)});
}
