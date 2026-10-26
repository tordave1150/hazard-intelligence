import type {Area, Forecast, Freshness, Metric} from './types';

export function freshness(records: Forecast[], now = Date.now()): Freshness {
  if (!records.length) return 'UNAVAILABLE';
  const times = records.flatMap(r => [Date.parse(r.valid_periods[0]?.valid_start), Date.parse(r.fetched_at)]);
  if (times.some(t => !Number.isFinite(t))) return 'UNKNOWN';
  if (times.some(t => t > now + 3600000)) return 'UNKNOWN';
  const age = (now - Math.min(...times)) / 3600000;
  return age <= 30 ? 'FRESH' : age <= 48 ? 'DELAYED' : 'STALE';
}

export function contains(area: Area, child: Area) {
  return area.id === child.id || area.level === 'national' || child.parent_id === area.id ||
    child.region_id === area.id || child.province_id === area.id;
}

export const metricLabel = (metric: Metric) => metric === 'rainfall_mm' ? 'Forecast rainfall' : 'Chance of rain';
export const metricUnit = (metric: Metric) => metric === 'rainfall_mm' ? 'mm / 24h' : '%';
export function metricValue(record: Forecast | undefined, date: string, metric: Metric) {
  return record?.valid_periods.find(p => p.date === date)?.[metric] ?? null;
}
export function metricColor(value: number | null, metric: Metric): [number, number, number, number] {
  if (value === null || !Number.isFinite(value)) return [148,163,184,85];
  const breaks = metric === 'rainfall_mm' ? [1,10,25,50] : [20,40,60,80];
  const colors: [number,number,number,number][] = [[208,237,236,170],[146,211,205,185],[74,172,175,200],[30,123,151,215],[17,79,118,230]];
  return colors[breaks.filter(b=>value>=b).length];
}
export function bangkokTime(time: string | null | undefined) {
  if (!time || !Number.isFinite(Date.parse(time))) return 'Not provided';
  return new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Bangkok',day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(time)) + ' ICT';
}
export function ageLabel(time: string | null | undefined, now=Date.now()) {
  if (!time || !Number.isFinite(Date.parse(time))) return 'Unknown age';
  const hours=Math.floor((now-Date.parse(time))/3600000);
  return hours < 0 ? 'Future valid period' : hours < 1 ? 'Less than 1h ago' : hours < 24 ? `${hours}h ago` : `${Math.floor(hours/24)}d ${hours%24}h ago`;
}
