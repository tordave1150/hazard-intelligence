// Conservative application reservations, not the provider's billing meter.
// Keep today and the preceding 31 UTC dates, covering at least 31 full days.
export const radarUploadLimit=1800;
type Reservation={day:string;count:number};
export function reserveRadarUploads(value:unknown,count:number,now=Date.now()){
  const today=new Date(now).toISOString().slice(0,10),cutoff=new Date(Date.parse(today)-31*86400000).toISOString().slice(0,10);
  const initial=value===undefined||value===null;
  const rows=initial?[{day:today,count:100}]:value;
  if(!Array.isArray(rows)||rows.length>32||!Number.isSafeInteger(count)||count<0||count>7)throw Error('Invalid radar upload reservations');
  const seen=new Set<string>();
  const retained:Reservation[]=[];
  for(const row of rows){
    if(!row||typeof row.day!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(row.day)||!Number.isFinite(Date.parse(row.day))||
      new Date(row.day).toISOString().slice(0,10)!==row.day||row.day>today||!Number.isSafeInteger(row.count)||row.count<0||row.count>radarUploadLimit||seen.has(row.day))throw Error('Invalid radar upload reservations');
    seen.add(row.day);
    if(row.day>=cutoff)retained.push({day:row.day,count:row.count});
  }
  const used=retained.reduce((n,row)=>n+row.count,0);
  if(used+count>radarUploadLimit)throw Error('Radar upload budget exhausted');
  const current=retained.find(row=>row.day===today);
  if(current)current.count+=count;else retained.push({day:today,count});
  return {reservations:retained.sort((a,b)=>a.day.localeCompare(b.day)),reserved:used+count,remaining:radarUploadLimit-used-count,limit:radarUploadLimit};
}
