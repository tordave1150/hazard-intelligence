import {NextResponse} from 'next/server';
import {authorizeRadar} from '@/lib/radar-auth';
import {publishRadar} from '@/lib/radar-ingest';
import {readRadarSnapshot} from '@/lib/radar-snapshot';
import {invalid,json} from '@/lib/http';
export const runtime='nodejs';
export const dynamic='force-dynamic';
export const maxDuration=240;
export async function GET(request:Request){
  if(new URL(request.url).search)return invalid('Radar uses a national image sequence; no query parameters');
  return json({...await readRadarSnapshot(),deployment_commit:process.env.VERCEL_GIT_COMMIT_SHA??null});
}
export async function POST(request:Request){
  if(process.env.VERCEL_ENV&&process.env.VERCEL_ENV!=='production')return invalid('Ingestion is production-only',403);
  let run;
  try{run=await authorizeRadar(request.headers.get('authorization'));}catch{return invalid('Unauthorized',401);}
  if(request.headers.get('content-type')?.split(';')[0]!=='application/json')return invalid('Expected JSON',415);
  if(Number(request.headers.get('content-length'))>4000000)return invalid('Capture too large',413);
  const reader=request.body?.getReader();if(!reader)return invalid('Missing capture');
  const chunks:Uint8Array[]=[];let size=0;
  try{
    while(true){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>4000000){await reader.cancel();return invalid('Capture too large',413);}chunks.push(value);}
    const payload=JSON.parse(Buffer.concat(chunks).toString('utf8'));
    const result=await publishRadar(payload,run);
    return NextResponse.json(result,{headers:{'Cache-Control':'no-store'}});
  }catch(error){console.error('radar_receiver_failed',{error_type:error instanceof Error?error.name:'Error'});return invalid('Radar capture rejected or publication unavailable',503);}
}
