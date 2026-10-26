import Ajv from 'ajv/dist/2020';
import addFormats from 'ajv-formats';
import schema from '../../../packages/contracts/schema.json';
import type {DamObservation,Forecast} from './types';
import {damById,damLicenseUrl,damMetadataUrl,damSourceUrl} from './dams';
import {bangkokDate} from './semantics';
const ajv = new Ajv({strict: false, allErrors: false});
addFormats(ajv);
ajv.addSchema(schema);
const validate = ajv.compile<Forecast>({$ref:`${schema.$id}#/$defs/Forecast`});
const validateDam=ajv.compile<DamObservation>({$ref:`${schema.$id}#/$defs/DamObservation`});
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
