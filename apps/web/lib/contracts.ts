import Ajv from 'ajv/dist/2020';
import addFormats from 'ajv-formats';
import schema from '../../../packages/contracts/schema.json';
import type {DamObservation,Forecast,WarningFeed} from './types';
import {allowedWarningDocument} from './warnings';
import {areaById} from './geography';
import {damById,damLicenseUrl,damMetadataUrl,damSourceUrl} from './dams';
import {bangkokDate} from './semantics';
const ajv = new Ajv({strict: false, allErrors: false});
addFormats(ajv);
ajv.addSchema(schema);
const validate = ajv.compile<Forecast>({$ref:`${schema.$id}#/$defs/Forecast`});
const validateDam=ajv.compile<DamObservation>({$ref:`${schema.$id}#/$defs/DamObservation`});
const validateWarnings=ajv.compile<WarningFeed>({$ref:`${schema.$id}#/$defs/WarningFeed`});
export function validatedWarningFeed(value:unknown):WarningFeed{
  if(!validateWarnings(value))throw new Error('Stored CAP feed does not match contract');
  const feed=value as WarningFeed;
  if(feed.feed_item_count!==feed.records.length+feed.ignored_item_count||new Set(feed.records.map(r=>r.warning_id)).size!==feed.records.length)throw new Error('Incomplete CAP feed');
  if(Date.parse(feed.fetched_at)>Date.parse(feed.ingested_at)||Date.parse(feed.feed_generated_at)>Date.parse(feed.fetched_at)+300000)throw new Error('Invalid CAP feed time');
  for(const row of feed.records){
    if(!allowedWarningDocument(row.content_ref)||!row.content_ref.endsWith(`/CAP${row.warning_id}.xml`))throw new Error('Invalid CAP provenance');
    if(Date.parse(row.issued_at)>Date.parse(row.fetched_at)+300000||Date.parse(row.fetched_at)>Date.parse(row.ingested_at))throw new Error('Invalid CAP message time');
    if(row.references.some(ref=>ref.sender!=='TMD'||Date.parse(ref.issued_at)>Date.parse(row.issued_at)))throw new Error('Invalid CAP reference');
    if(row.message_type!=='Alert'&&!row.references.length)throw new Error('Missing CAP reference');
    if(row.message_type!=='Cancel'&&[row.effective_start,row.event,row.headline,row.language,row.agency_severity,row.urgency,row.certainty].some(v=>v===null))throw new Error('Missing CAP information');
    if(row.expires_at&&(!row.effective_start||Date.parse(row.expires_at)<=Date.parse(row.effective_start)))throw new Error('Invalid CAP interval');
    const sourceCodes=row.source_areas.flatMap(a=>a.geocodes.filter(c=>c.value_name==='ISO3166-2').map(c=>c.value));
    // Unrecognized agency codes remain verbatim in source_areas. Only exact,
    // known province references may enter canonical area_ids.
    const codes=new Set(sourceCodes.filter(code=>/^TH-[0-9]{2}$/.test(code))
      .map(code=>'TH-P-'+code.slice(3)).filter(id=>areaById.get(id)?.level==='province'));
    if(codes.size!==row.area_ids.length||row.area_ids.some(id=>!codes.has(id)||areaById.get(id)?.level!=='province'))throw new Error('Unverified CAP province');
    let vertices=0;
    for(const [ring] of row.geometry?.coordinates??[]){
      vertices+=ring.length;
      if(ring[0][0]!==ring.at(-1)![0]||ring[0][1]!==ring.at(-1)![1]||ring.some(([lon,lat])=>lon<96||lon>107||lat<5||lat>22))throw new Error('Invalid CAP polygon');
    }
    if(vertices>100000)throw new Error('CAP geometry too large');
  }
  return feed;
}
export function validatedDam(value:unknown):DamObservation{
  if(!validateDam(value))throw new Error('Stored dam report does not match contract');
  const record=value as DamObservation,meta=damById.get(record.dam_id);
  if(!meta||record.source_dam_id!==meta.source_dam_id||record.name_th!==meta.name_th||
    record.point.lat!==meta.point.lat||record.point.lon!==meta.point.lon||record.province_id!==meta.province_id||
    record.district_id!==meta.district_id||record.region_id!==meta.region_id)throw new Error('Unverified dam geography');
  if(Date.parse(record.fetched_at)>Date.parse(record.ingested_at))throw new Error('Invalid dam retrieval time');
  if(record.source_url!==damSourceUrl||record.metadata_url!==damMetadataUrl||record.license_url!==damLicenseUrl)throw new Error('Unverified dam provenance');
  if(record.report_date>bangkokDate(Date.parse(record.fetched_at)))throw new Error('Future dam report');
  if(record.maximum_capacity_mcm!==null&&record.normal_capacity_mcm!==null&&record.maximum_capacity_mcm<record.normal_capacity_mcm)throw new Error('Invalid dam capacity');
  if(record.storage_pct!==null&&record.storage_volume_mcm!==null&&record.normal_capacity_mcm!==null&&record.normal_capacity_mcm>0&&
    Math.abs(record.storage_pct-record.storage_volume_mcm/record.normal_capacity_mcm*100)>.08)throw new Error('Invalid dam percentage denominator');
  return record;
}
export function validatedForecast(value: unknown): Forecast {
  if (!validate(value)) throw new Error('Stored forecast does not match contract');
  const record = value as Forecast;
  const dates = record.valid_periods.map(p=>p.date);
  if (new Set(dates).size !== dates.length || dates.join() !== [...dates].sort().join()) throw new Error('Invalid forecast dates');
  for (const p of record.valid_periods) {
    const expectedStart=Date.parse(`${p.date}T00:00:00+07:00`);
    if (Date.parse(p.valid_start)!==expectedStart || Date.parse(p.valid_end)!==expectedStart+86400000) throw new Error('Invalid Bangkok accumulation window');
  }
  return record;
}
