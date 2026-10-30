import registry from '@/data/source-registry.json';
import {readSnapshot} from '@/lib/snapshot';
import {readDamSnapshot} from '@/lib/dam-snapshot';
import {readWarningSnapshot} from '@/lib/warning-snapshot';
import {readFloodSnapshot} from '@/lib/flood-snapshot';
import {readHourlySnapshot} from '@/lib/hourly-snapshot';
import {readGaugeSnapshot} from '@/lib/gauge-snapshot';
import {readRainSnapshot} from '@/lib/rain-snapshot';
import {json} from '@/lib/http';
import {monitorSource} from '@/lib/source-health';
import type {Freshness} from '@/lib/types';
export const dynamic='force-dynamic';
export async function GET(){
  const [weather,dams,warnings,floods,hourly,gauges,rain]=await Promise.all([readSnapshot(),readDamSnapshot(),readWarningSnapshot(),readFloodSnapshot(),readHourlySnapshot(),readGaugeSnapshot(),readRainSnapshot()]);
  const states:Record<string,{freshness:Freshness;health:Record<string,unknown>|null;storage:string;query_freshness?:Freshness;available?:boolean;scope_area_id?:string|null}>={
    open_meteo:{freshness:weather.freshness,health:weather.status,storage:weather.storage},
    rid:{freshness:dams.freshness,health:dams.health,storage:dams.storage},tmd:{freshness:warnings.freshness,health:warnings.health,storage:warnings.storage},
    gistda:{freshness:floods.freshness,health:floods.health,storage:floods.storage,query_freshness:floods.query_freshness,available:!!floods.feed,scope_area_id:floods.feed?.area_id??null},
    open_meteo_hourly:{freshness:hourly.freshness,health:hourly.health,storage:hourly.storage},
    thaiwater:{freshness:gauges.freshness,health:gauges.health,storage:gauges.storage,query_freshness:gauges.query_freshness,available:!!gauges.feed,scope_area_id:'TH'},
    thaiwater_rain:{freshness:rain.freshness,health:rain.health,storage:rain.storage,query_freshness:rain.query_freshness,available:!!rain.feed,scope_area_id:'TH'},
  };
  const now=Date.now();
  return json({checked_at:new Date(now).toISOString(),sources:registry.map(source=>{
    const state=states[source.id]??{freshness:'UNAVAILABLE' as const,health:null,storage:'unconfigured'};
    return {...source,...state,monitoring:monitorSource(source.id,state.query_freshness??state.freshness,state.health,now)};
  })});
}
