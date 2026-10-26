import {readSnapshot} from '@/lib/snapshot';
import {json} from '@/lib/http';
export const runtime='nodejs';
export const dynamic='force-dynamic';
export async function GET() {
  const snapshot=await readSnapshot();
  return json({...snapshot,available_dates:[...new Set(snapshot.records.flatMap(r=>r.valid_periods.map(p=>p.date)))].sort()});
}
