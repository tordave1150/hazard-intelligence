import Ajv from 'ajv/dist/2020';
import addFormats from 'ajv-formats';
import schema from '../../../packages/contracts/schema.json';
import type {DamObservation,Forecast,WarningFeed,FloodFeed,FloodChunk,HourlyForecast,GaugeFeed} from './types';
import {allowedWarningDocument} from './warnings';
import {areaById} from './geography';
import {damById,damLicenseUrl,damMetadataUrl,damSourceUrl} from './dams';
import {bangkokDate} from './semantics';
import {wallOrdinal} from './gauge-history-data';
const ajv = new Ajv({strict: false, allErrors: false});
addFormats(ajv);
ajv.addSchema(schema);
const validate = ajv.compile<Forecast>({$ref:`${schema.$id}#/$defs/Forecast`});
const validateDam=ajv.compile<DamObservation>({$ref:`${schema.$id}#/$defs/DamObservation`});
const validateWarnings=ajv.compile<WarningFeed>({$ref:`${schema.$id}#/$defs/WarningFeed`});
const validateNationalFlood=ajv.compile<FloodFeed>({$ref:`${schema.$id}#/$defs/GistdaNationalFloodFeed`});
const validateThreeDayFlood=ajv.compile<FloodFeed>({$ref:`${schema.$id}#/$defs/GistdaThreeDayFeed`});
const validateThreeDayChunk=ajv.compile<FloodChunk>({$ref:`${schema.$id}#/$defs/GistdaThreeDayChunk`});
const validateHourly=ajv.compile<HourlyForecast>({$ref:`${schema.$id}#/$defs/HourlyForecast`});
const validateGauge=ajv.compile<GaugeFeed>({$ref:`${schema.$id}#/$defs/ThaiWaterFeed`});
export function validatedGaugeFeed(value:unknown):GaugeFeed{
  if(!validateGauge(value))throw Error('Invalid station feed contract');
  const feed=value as GaugeFeed,ids=[...feed.records.map(r=>r.source_station_id),...feed.excluded_stations.map(r=>r.source_station_id)];
  if(feed.record_count!==feed.records.length||ids.length!==feed.provider_automatic_count||new Set(ids).size!==ids.length||
    Date.parse(feed.fetched_at)>Date.parse(feed.ingested_at)||feed.time_unknown_count!==feed.record_count||
    feed.quality_issue_count!==feed.records.filter(r=>r.quality_flags.length).length)throw Error('Incomplete station response');
  const counts=new Map<string,number>();
  for(const row of feed.records){
    const province=areaById.get(row.province_id),district=row.district_id?areaById.get(row.district_id):null;
    if(!province||province.level!=='province'||row.region_id!==province.region_id||row.gauge_id!=='THW-'+row.source_station_id||
      row.district_id&&district?.province_id!==row.province_id)throw Error('Invalid station administrative identity');
    if((row.point===null)!==row.quality_flags.includes('INVALID_POINT')||
      [row.water_level_m,row.water_level_msl].some(v=>v!==null&&!Number.isFinite(v)))throw Error('Invalid station value');
    let validTime=false;try{if(row.source_observed_at){wallOrdinal(row.source_observed_at);validTime=true;}}catch{}
    if((!validTime)!==row.quality_flags.includes('INVALID_PROVIDER_TIME')||
      (row.water_level_m===null&&row.water_level_msl===null)!==row.quality_flags.includes('NO_LEVEL'))throw Error('Unflagged station quality issue');
    counts.set(row.province_id,(counts.get(row.province_id)??0)+1);
  }
  const expected=[...counts].sort(([a],[b])=>a.localeCompare(b)).map(([area_id,record_count])=>({area_id,record_count}));
  if(JSON.stringify(expected)!==JSON.stringify(feed.coverage_by_province)||new TextEncoder().encode(JSON.stringify(feed)).length>4*1024*1024)throw Error('Invalid station coverage');
  return feed;
}
export function validatedHourly(value:unknown):HourlyForecast{
  if(!validateHourly(value))throw new Error('Invalid hourly forecast contract');
  const record=value as HourlyForecast,start=Date.parse(record.forecast_date+'T00:00:00+07:00'),area=areaById.get(record.location_id);
  if(!area||!['province','district'].includes(area.level)||area.lat!==record.point.lat||area.lon!==record.point.lon)throw new Error('Invalid hourly point identity');
  if(record.forecast_date!==bangkokDate(Date.parse(record.fetched_at))||record.forecast_date!==bangkokDate(Date.parse(record.ingested_at))||Date.parse(record.fetched_at)>Date.parse(record.ingested_at))throw new Error('Invalid hourly dates');
  for(const [index,hour] of record.valid_hours.entries()){
    if(Date.parse(hour.valid_start)!==start+index*3600000||Date.parse(hour.valid_end)!==start+(index+1)*3600000||hour.temperature_valid_at!==hour.valid_end)throw new Error('Invalid preceding-hour interval');
  }
  return record;
}
export function validatedFloodFeed(value:unknown):FloodFeed{
  if(!validateNationalFlood(value)&&!validateThreeDayFlood(value))throw new Error('Stored GISTDA snapshot does not match contract');
  const feed=value as FloodFeed;
  const national=feed.area_id==='TH';
  if(feed.record_count!==feed.records.length||new Set(feed.records.map(r=>r.id)).size!==feed.records.length)throw new Error('Incomplete GISTDA query');
  if(Date.parse(feed.fetched_at)>Date.parse(feed.ingested_at)||Date.parse(feed.response_at)>Date.parse(feed.fetched_at)+300000)throw new Error('Invalid GISTDA time');
  if(new TextEncoder().encode(JSON.stringify(feed)).length>(feed.product_window==='3days'?32:national?4:2)*1024*1024)throw new Error('GISTDA response too large');
  if(national&&(!feed.record_count?feed.page_count!==1:!feed.page_count||feed.page_count>feed.record_count||feed.record_count>feed.page_count*100))throw new Error('Invalid GISTDA page accounting');
  checkedFloodRows(feed.records,national,feed.product_window==='3days');
  return feed;
}
function checkedFloodRows(records:FloodFeed['records'],national:boolean,threeDay:boolean){
  const bounds=areaById.get('TH')!.bbox;let positions=0,rings=0;
  for(const row of records){
    if(national){
      const [province,district]=row.area_ids??[],member=areaById.get(district);
      if(!member||member.level!=='district'||member.province_id!==province)throw new Error('Invalid GISTDA administrative hierarchy');
    }
    let featureRings=0;
    const polygons=row.geometry.type==='Polygon'?[row.geometry.coordinates]:row.geometry.coordinates;
    for(const polygon of polygons)for(const ring of polygon){
      positions+=ring.length;rings++;featureRings++;
      if(ring[0].length!==ring.at(-1)!.length||ring[0].some((v,i)=>v!==ring.at(-1)![i]))throw new Error('Unclosed GISTDA ring');
      if(ring.some(p=>p.length!==ring[0].length||p.some(v=>!Number.isFinite(v))||p[0]<bounds[0]||p[0]>bounds[2]||p[1]<bounds[1]||p[1]>bounds[3]))throw new Error('Invalid GISTDA position');
    }
    if(featureRings>256)throw new Error('GISTDA feature ring limit exceeded');
  }
  if(positions>(threeDay?2000000:national?100000:20000)||rings>256*(threeDay?20000:national?1000:100))throw new Error('GISTDA geometry limit exceeded');
}
export function validatedFloodChunk(value:unknown):FloodChunk{
  if(!validateThreeDayChunk(value))throw new Error('Invalid three-day GISTDA chunk');
  const chunk=value as FloodChunk,feed=chunk.feed;
  if(Number(chunk.chunk_id)>=chunk.chunk_count||chunk.records.length>feed.record_count)throw new Error('Invalid GISTDA chunk accounting');
  if(Date.parse(feed.fetched_at)>Date.parse(feed.ingested_at)||Date.parse(feed.response_at)>Date.parse(feed.fetched_at)+300000)throw new Error('Invalid GISTDA time');
  if(!feed.record_count?feed.page_count!==1:!feed.page_count||feed.page_count>feed.record_count||feed.record_count>feed.page_count*100)throw new Error('Invalid GISTDA page accounting');
  if(new TextEncoder().encode(JSON.stringify(chunk)).length>1024*1024)throw new Error('GISTDA chunk too large');
  if(!chunk.records.length&&feed.record_count)throw new Error('Unexpected empty GISTDA chunk');
  if(new Set(chunk.records.map(row=>row.id)).size!==chunk.records.length)throw new Error('Duplicate GISTDA chunk features');
  checkedFloodRows(chunk.records,true,true);
  return chunk;
}
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
    const timeQuality=!row.effective_start||!row.expires_at?'NOT_SUPPLIED':Date.parse(row.expires_at)<=Date.parse(row.effective_start)?'INVALID_PROVIDER_INTERVAL':'VALID_INTERVAL';
    if(row.time_quality&&row.time_quality!==timeQuality)throw new Error('CAP time quality does not match timestamps');
    if(timeQuality==='INVALID_PROVIDER_INTERVAL'&&row.time_quality!==timeQuality)throw new Error('Unflagged invalid CAP interval');
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
