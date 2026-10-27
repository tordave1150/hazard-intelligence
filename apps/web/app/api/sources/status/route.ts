import registry from '@/data/source-registry.json';
import {readSnapshot} from '@/lib/snapshot';
import {readDamSnapshot} from '@/lib/dam-snapshot';
import {readWarningSnapshot} from '@/lib/warning-snapshot';
import {readFloodSnapshot} from '@/lib/flood-snapshot';
import {json} from '@/lib/http';
export const dynamic='force-dynamic';
export async function GET() {
  const [snapshot,dams,warnings,floods]=await Promise.all([readSnapshot(),readDamSnapshot(),readWarningSnapshot(),readFloodSnapshot()]);
  return json({sources:registry.map(source=>({...source,freshness:source.id==='open_meteo'?snapshot.freshness:source.id==='rid'?dams.freshness:source.id==='tmd'?warnings.freshness:source.id==='gistda'?floods.freshness:'UNAVAILABLE',
    health:source.id==='open_meteo'?snapshot.status:source.id==='rid'?dams.health:source.id==='tmd'?warnings.health:source.id==='gistda'?floods.health:null,
    storage:source.id==='open_meteo'?snapshot.storage:source.id==='rid'?dams.storage:source.id==='tmd'?warnings.storage:source.id==='gistda'?floods.storage:null,
    ...(source.id==='gistda'?{available:floods.feed!==null,query_freshness:floods.query_freshness,scope_area_id:'TH-D-2604'}:{})}))});
}
