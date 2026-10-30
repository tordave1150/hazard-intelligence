import type {GaugeHistory} from './types';

/** A calendar ordinal only: this does not assign a timezone to an observation. */
export function wallOrdinal(value:string):number{
  if(!/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/.test(value))throw Error('Invalid provider calendar time');
  const stamp=Date.parse(value.replace(' ','T')+':00Z');
  if(!Number.isFinite(stamp)||new Date(stamp).toISOString().slice(0,16).replace('T',' ')!==value)throw Error('Invalid provider calendar date');
  return stamp;
}
export function parseGaugeHistory(payload:unknown,context:Omit<GaugeHistory,'points'|'invalid_value_count'>):GaugeHistory{
  const value=payload as {result?:string;data?:{graph_data?:unknown[]}};
  if(value?.result!=='OK'||!Array.isArray(value.data?.graph_data)||value.data.graph_data.length>2016)throw Error('Invalid station history response');
  let invalid=0;const seen=new Set<string>();
  const points=value.data.graph_data.map(item=>{
    const row=item as {datetime?:string;value?:unknown};
    if(typeof row?.datetime!=='string'||seen.has(row.datetime))throw Error('Invalid or duplicate station history time');
    wallOrdinal(row.datetime);seen.add(row.datetime);
    if(row.datetime.slice(0,10)<context.start_date||row.datetime.slice(0,10)>context.end_date)throw Error('Station history outside requested dates');
    const numeric=typeof row.value==='number'?row.value:typeof row.value==='string'&&/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(row.value)?Number(row.value):null;
    const level=numeric!==null&&Number.isFinite(numeric)&&Math.abs(numeric)<=10000?numeric:null;
    if(row.value!==null&&row.value!==undefined&&level===null)invalid++;
    return {source_observed_at:row.datetime,value:level};
  }).sort((a,b)=>a.source_observed_at.localeCompare(b.source_observed_at));
  return {...context,points,invalid_value_count:invalid};
}
