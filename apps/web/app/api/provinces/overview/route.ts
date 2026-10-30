import {readRainSnapshot} from '@/lib/rain-snapshot';
import {readSnapshot} from '@/lib/snapshot';
import {readDamSnapshot} from '@/lib/dam-snapshot';
import {readGaugeSnapshot} from '@/lib/gauge-snapshot';
import {readWarningSnapshot} from '@/lib/warning-snapshot';
import {readFloodProvinceCounts} from '@/lib/flood-area-snapshot';
import {buildProvinceOverview} from '@/lib/provinces';
import {invalid,json} from '@/lib/http';
export const dynamic='force-dynamic';
export const runtime='nodejs';
export async function GET(request:Request){
  if(new URL(request.url).search)return invalid('Province overview uses current source snapshots and Today only');
  const values=await Promise.all([readSnapshot(),readDamSnapshot(),readGaugeSnapshot(),readWarningSnapshot(),readFloodProvinceCounts(),readRainSnapshot()]);
  return json(buildProvinceOverview(...values));
}
