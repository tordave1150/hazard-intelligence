import registry from '@/data/source-registry.json';
import {readSnapshot} from '@/lib/snapshot';
import {readDamSnapshot} from '@/lib/dam-snapshot';
import {readWarningSnapshot} from '@/lib/warning-snapshot';
import {readFloodSnapshot} from '@/lib/flood-snapshot';
import {readHourlySnapshot} from '@/lib/hourly-snapshot';
import {json} from '@/lib/http';
import {monitorSource} from '@/lib/source-health';
export const dynamic='force-dynamic';
export async function GET() {
  const [snapshot,dams,warnings,floods,hourly]=await Promise.all([readSnapshot(),readDamSnapshot(),readWarningSnapshot(),readFloodSnapshot(),readHourlySnapshot()]);
  const now=Date.now();
  return json({checked_at:new Date(now).toISOString(),sources:registry.map(source=>{
    const state={...source,freshness:source.id==='open_meteo'?snapshot.freshness:source.id==='open_meteo_hourly'?hourly.freshness:source.id==='rid'?dams.freshness:source.id==='tmd'?warnings.freshness:source.id==='gistda'?floods.freshness:'UNAVAILABLE',
    health:source.id==='open_meteo'?snapshot.status:source.id==='open_meteo_hourly'?hourly.health:source.id==='rid'?dams.health:source.id==='tmd'?warnings.health:source.id==='gistda'?floods.health:null,
    storage:source.id==='open_meteo'?snapshot.storage:source.id==='open_meteo_hourly'?hourly.storage:source.id==='rid'?dams.storage:source.id==='tmd'?warnings.storage:source.id==='gistda'?floods.storage:null,
    ...(source.id==='gistda'?{available:floods.feed!==null,query_freshness:floods.query_freshness,scope_area_id:floods.feed?.area_id??null}:{})};
    return {...state,monitoring:monitorSource(source.id,source.id==='gistda'?floods.query_freshness:state.freshness as typeof snapshot.freshness,state.health,now)};
  })});
}
