import data from '../data/areas.json';
import type {Area, Level} from './types';
import {contains} from './semantics';
export const areas = data as Area[];
export const areaById = new Map(areas.map(a=>[a.id,a]));
export const national = areaById.get('TH')!;
export function areaMembers(id: string, level?: Level) {
  const area=areaById.get(id);
  if (!area) throw new Error('Unknown area');
  return areas.filter(a=>contains(area,a) && (!level || a.level===level));
}
