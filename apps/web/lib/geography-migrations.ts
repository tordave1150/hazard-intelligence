import corrections from '../../../data/geography/dopa-corrections.json';
import type {Forecast} from './types';

export const geographyIdentityMigrations=corrections.id_aliases.map(alias=>({
  from:alias.from,to:alias.to,reference:corrections.download_url,source_as_of:corrections.source_as_of
}));

// Only this verified old ID at its original requested point is compatible.
// Preserve every measurement, model point and time; do not mutate the input.
export function canonicalStoredForecast(record:Forecast):Forecast {
  const alias=corrections.id_aliases.find(a=>a.from===record.location_id);
  if(!alias)return record;
  if(record.point.lat!==alias.point.lat||record.point.lon!==alias.point.lon)throw new Error('Historical forecast point mismatch');
  return {...record,location_id:alias.to};
}
