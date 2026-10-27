import {readWarningSnapshot} from '@/lib/warning-snapshot';
import {warningInArea,warningState,warningUnmappedCodes} from '@/lib/warnings';
import {areas,areaById} from '@/lib/geography';
import {invalid,json} from '@/lib/http';
export const dynamic='force-dynamic';
export const runtime='nodejs';
export async function GET(request:Request){
  const params=new URL(request.url).searchParams;
  if([...params.keys()].some(key=>key!=='area_id'))return invalid('Invalid warning query');
  const area=areaById.get(params.get('area_id')??'TH');if(!area)return invalid('Unknown area',404);
  const snapshot=await readWarningSnapshot();const records=snapshot.records.filter(r=>warningInArea(r,area,areas));
  return json({...snapshot,records,status:snapshot.freshness,
    source_id:'tmd',integration_status:'accepted',current_count:records.filter(r=>warningState(r,snapshot.records)==='CURRENT').length,
    message_states:Object.fromEntries(records.map(row=>[row.warning_id,warningState(row,snapshot.records)])),
    geography_issues:{scope:'Entire latest feed; unresolved codes are not assigned to the requested area',
      unmapped_geocodes:snapshot.records.flatMap(row=>warningUnmappedCodes(row).map(code=>({warning_id:row.warning_id,...code})))},
    coverage:'Latest public CAP feed only; absence does not establish safe conditions or complete warning coverage. Province filters use recognized codes only; unmapped agency codes are retained without inferring a province or region.'});
}
