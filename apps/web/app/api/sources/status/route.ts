import registry from '@/data/source-registry.json';
import {readSnapshot} from '@/lib/snapshot';
import {json} from '@/lib/http';
export const dynamic='force-dynamic';
export async function GET() {
  const snapshot=await readSnapshot();
  return json({sources:registry.map(source=>({...source,freshness:source.id==='open_meteo'?snapshot.freshness:'UNAVAILABLE',
    health:source.id==='open_meteo'?snapshot.status:null,storage:source.id==='open_meteo'?snapshot.storage:null}))});
}
