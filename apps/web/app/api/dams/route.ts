import {readDamSnapshot} from '@/lib/dam-snapshot';
import {damInArea,damMetadata} from '@/lib/dams';
import {areaById} from '@/lib/geography';
import {invalid,json} from '@/lib/http';
export const runtime='nodejs';
export const dynamic='force-dynamic';
export async function GET(request:Request){
  const params=new URL(request.url).searchParams;
  if([...params.keys()].some(key=>key!=='area_id'))return invalid('Invalid dam query');
  const id=params.get('area_id')??'TH',area=areaById.get(id);
  if(!area)return invalid('Unknown area',404);
  const snapshot=await readDamSnapshot();
  return json({...snapshot,records:snapshot.records.filter(d=>damInArea(d,area)),status:snapshot.freshness,
    source_id:'rid',integration_status:'accepted',report_date:snapshot.records[0]?.report_date??null,total_count:damMetadata.length});
}
