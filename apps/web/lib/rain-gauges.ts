import type {Area,RainSnapshot} from './types';
import {gaugeInArea} from './gauges';
export function rainResponse(snapshot:RainSnapshot,area:Area,summary=false){
  const records=snapshot.records.filter(r=>gaugeInArea(r,area));
  return {...snapshot,records:summary?[]:records,detail_loaded:!summary,source_id:'thaiwater',product_id:'national_rain_24h',selected_area_id:area.id,scope_area_id:'TH',
    total_count:snapshot.feed?.record_count??null,selected_count:snapshot.feed?records.length:null,
    status:!snapshot.feed?'UNAVAILABLE':records.length?'AVAILABLE':'EMPTY_RESULT',observation_time_status:'TIMEZONE_NOT_SUPPLIED'};
}
