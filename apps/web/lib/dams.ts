import metadata from '../data/rid-dams.json';
import basinMembership from '../data/dam-basin-membership.json';
import type {Area,DamMeta,DamObservation,Freshness} from './types';
export const damMetadata=metadata.dams as DamMeta[];
export const damSourceUrl='https://app.rid.go.th/reservoir/api/dam/public';
export const damMetadataUrl=metadata.source_page;
export const damLicenseUrl=metadata.license_url;
export const damById=new Map(damMetadata.map(d=>[d.dam_id,d]));
export const damBasinId=(id:string)=>(basinMembership as Record<string,string|null>)[id]??null;
export function damInArea(dam:DamMeta,area:Area){
  if(area.level==='basin')return (basinMembership as Record<string,string|null>)[dam.dam_id]===area.id;
  return area.level==='national'||area.id===dam.region_id||area.id===dam.province_id||area.id===dam.district_id;
}
export function damFreshness(records:DamObservation[],now=Date.now()):Freshness{
  if(!records.length)return 'UNAVAILABLE';
  const today=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Bangkok',year:'numeric',month:'2-digit',day:'2-digit'}).format(now);
  const dates=records.map(r=>Date.parse(r.report_date));
  const retrieved=records.map(r=>Date.parse(r.fetched_at));
  if([...dates,...retrieved].some(t=>!Number.isFinite(t))||dates.some(t=>t>Date.parse(today))||retrieved.some(t=>t>now+3600000))return 'UNKNOWN';
  const days=(Date.parse(today)-Math.min(...dates))/86400000;
  const hours=(now-Math.min(...retrieved))/3600000;
  return days===0&&hours<=30?'FRESH':days<=2&&hours<=48?'DELAYED':'STALE';
}
export function reportDate(date:string){
  return new Date(date+'T00:00:00+07:00').toLocaleDateString('en-GB',{timeZone:'Asia/Bangkok',day:'2-digit',month:'short',year:'numeric'});
}
