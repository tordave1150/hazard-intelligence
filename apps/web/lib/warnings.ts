import type {AgencyWarning,Area,Freshness,WarningDisplay,WarningFeed,WarningState} from './types';
export const warningFeedUrl='https://www.tmd.go.th/api/xml/CAP';
export const warningTermsUrl='https://www.tmd.go.th/content/copyright';
export const allowedWarningDocument=(url:string)=>/^https:\/\/www\.tmd\.go\.th\/uploads\/CAP\/CAPTMD[0-9A-Za-z_-]+\.xml$/.test(url);
const identity=(row:{sender:string;warning_id:string;issued_at:string})=>`${row.sender},${row.warning_id},${row.issued_at}`;
export function warningState(row:AgencyWarning,records:AgencyWarning[],now=Date.now()):WarningState{
  if(row.message_type==='Cancel')return 'CANCELLED';
  const replacement=records.filter(r=>(r.message_type==='Update'||r.message_type==='Cancel')&&r.references.some(ref=>identity(ref)===identity(row)))
    .sort((a,b)=>Date.parse(b.issued_at)-Date.parse(a.issued_at)||Number(b.message_type==='Cancel')-Number(a.message_type==='Cancel'))[0];
  if(replacement)return replacement.message_type==='Cancel'?'CANCELLED':'SUPERSEDED';
  if(!row.effective_start||!row.expires_at)return 'TIME_UNKNOWN';
  const start=Date.parse(row.effective_start),end=Date.parse(row.expires_at);
  if(!Number.isFinite(start)||!Number.isFinite(end)||end<=start)return 'TIME_UNKNOWN';
  return now>=end?'EXPIRED':now<start?'UPCOMING':'CURRENT';
}
export function warningFreshness(feed:Pick<WarningFeed,'fetched_at'|'feed_generated_at'>|null,now=Date.now(),failed=false):Freshness{
  if(!feed)return 'UNAVAILABLE';
  const fetched=Date.parse(feed.fetched_at),generated=Date.parse(feed.feed_generated_at);
  if(!Number.isFinite(fetched)||!Number.isFinite(generated)||Math.max(fetched,generated)>now+300000)return 'UNKNOWN';
  // Generation time is provider feed assembly, not message issuance or coverage.
  const hours=(now-Math.min(fetched,generated))/3600000;
  return hours<=2&&!failed?'FRESH':hours<=6?'DELAYED':'STALE';
}
export function warningInArea(row:AgencyWarning,area:Area,areas:Area[]){
  return area.level==='national'||row.area_ids.some(id=>id===area.id||id===area.province_id||
    (area.level==='region'&&areas.some(a=>a.id===id&&a.region_id===area.id)));
}
export function warningUnmappedCodes(row:AgencyWarning){
  const seen=new Set<string>();
  return row.source_areas.flatMap(area=>area.geocodes).filter(code=>{
    const key=JSON.stringify([code.value_name,code.value]);
    const mapped=code.value_name==='ISO3166-2'&&/^TH-[0-9]{2}$/.test(code.value)&&row.area_ids.includes('TH-P-'+code.value.slice(3));
    if(mapped||seen.has(key))return false;
    seen.add(key);return true;
  });
}
export function warningMapRecords(records:AgencyWarning[],selected:string|null,freshness:Freshness,now=Date.now()):WarningDisplay[]{
  // Keep issued validity-window boundaries visible as gray references when a
  // refresh is delayed; freshness still controls whether agency colors apply.
  const chosen=selected?records.filter(r=>r.warning_id===selected):records.filter(r=>warningState(r,records,now)==='CURRENT');
  return chosen.filter(r=>r.geometry).map(row=>({...row,display_state:warningState(row,records,now),
    archived:warningState(row,records,now)!=='CURRENT'||freshness!=='FRESH'}));
}
export const warningColor=(row:WarningDisplay)=>row.archived?'#7a8088':row.agency_severity==='Extreme'?'#b94741':row.agency_severity==='Severe'?'#bd6b30':'#a47d29';
