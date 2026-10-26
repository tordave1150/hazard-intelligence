import Ajv from 'ajv/dist/2020';
import addFormats from 'ajv-formats';
import schema from '../../../packages/contracts/schema.json';
import type {Forecast} from './types';
const ajv = new Ajv({strict: false, allErrors: false});
addFormats(ajv);
const validate = ajv.compile<Forecast>({...schema, $ref: '#/$defs/Forecast'});
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
