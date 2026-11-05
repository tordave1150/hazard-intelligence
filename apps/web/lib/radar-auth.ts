import {createRemoteJWKSet,jwtVerify,type JWTPayload} from 'jose';
const audience='https://hazard-intelligence-lime.vercel.app/api/radar';
const keys=createRemoteJWKSet(new URL('https://token.actions.githubusercontent.com/.well-known/jwks'),{timeoutDuration:5000});
export function acceptedRadarClaims(payload:JWTPayload){
  return payload.repository_id==='1433731657'&&payload.repository==='tordave1150/hazard-intelligence'&&payload.ref==='refs/heads/main'&&
    payload.workflow_ref==='tordave1150/hazard-intelligence/.github/workflows/radar.yml@refs/heads/main'&&
    ['schedule','workflow_dispatch','push','workflow_run'].includes(String(payload.event_name))&&payload.runner_environment==='github-hosted'&&
    /^\d+$/.test(String(payload.run_id))&&/^\d+$/.test(String(payload.run_attempt))&&
    typeof payload.iat==='number'&&typeof payload.exp==='number'&&payload.exp-payload.iat<=600;
}
export async function authorizeRadar(header:string|null,keySet:Parameters<typeof jwtVerify>[1]=keys){
  if(!header?.startsWith('Bearer ')||header.length>16000)throw Error('Unauthorized');
  const {payload}=await jwtVerify(header.slice(7),keySet,{issuer:'https://token.actions.githubusercontent.com',audience,algorithms:['RS256'],maxTokenAge:'10m',clockTolerance:5});
  if(!acceptedRadarClaims(payload))throw Error('Unauthorized');
  return {run_id:String(payload.run_id),run_attempt:String(payload.run_attempt),issued_at:payload.iat!,run_url:'https://github.com/tordave1150/hazard-intelligence/actions/runs/'+payload.run_id};
}
