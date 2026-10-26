import registry from '@/data/source-registry.json';
import {readSnapshot} from '@/lib/snapshot';
import {readDamSnapshot} from '@/lib/dam-snapshot';
import {json} from '@/lib/http';
export const dynamic='force-dynamic';
export async function GET() {
  const [snapshot,dams]=await Promise.all([readSnapshot(),readDamSnapshot()]);
  return json({sources:registry.map(source=>({...source,freshness:source.id==='open_meteo'?snapshot.freshness:source.id==='rid'?dams.freshness:'UNAVAILABLE',
    health:source.id==='open_meteo'?snapshot.status:source.id==='rid'?dams.health:null,storage:source.id==='open_meteo'?snapshot.storage:source.id==='rid'?dams.storage:null}))});
}
