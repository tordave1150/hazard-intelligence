import type {RainSnapshot} from './types';
export async function loadRainSnapshot(previous:RainSnapshot,details:boolean,signal:AbortSignal,request:typeof fetch=fetch):Promise<RainSnapshot>{
  const response=await request('/api/gauges?kind=rain&view=summary',{cache:'no-store',signal});if(!response.ok)throw Error('Rain summary unavailable');
  const summary=await response.json() as RainSnapshot;
  if(summary.feed&&previous.feed?.fetched_at===summary.feed.fetched_at&&previous.detail_loaded)return {...summary,records:previous.records,detail_loaded:true};
  if(!summary.feed||!details)return summary;
  const full=await request('/api/gauges?kind=rain',{cache:'no-store',signal});if(!full.ok)throw Error('Rain stations unavailable');
  const value=await full.json() as RainSnapshot;
  if(!value.feed||!value.detail_loaded||value.records.length!==value.feed.record_count||new Set(value.records.map(r=>r.gauge_id)).size!==value.records.length)throw Error('Incomplete rain station response');
  return value;
}
