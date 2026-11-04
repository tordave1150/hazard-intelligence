import {describe,it,expect,beforeAll} from 'vitest';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {SignJWT,generateKeyPair} from 'jose';
import {authorizeRadar,acceptedRadarClaims} from '../lib/radar-auth';
import {decodedRadarCandidate} from '../lib/radar-capture';
import {radarPng} from '../lib/radar-png';
import {validatedRadar,radarFreshness,radarVisible,radarMissingSlots,radarControlPixel,type RadarManifest} from '../lib/radar';
import {effectiveBackground,backgroundAvailable} from '../lib/map-layer-state';
import {reserveRadarUploads} from '../lib/radar-budget';
import {monitorSource} from '../lib/source-health';
const png=readFileSync(new URL('../../../tests/fixtures/radar/synthetic-transparent.png',import.meta.url));
const checked=radarPng(png),now=Date.parse('2026-11-04T12:46:00Z');
const frame={...checked,observed_at:'2026-11-04T12:45:00Z',url:'https://fixture.public.blob.vercel-storage.com/tmd-radar/20261104T124500Z-'+checked.sha256+'.png'};
const feed:RadarManifest={schema_version:'2.0',source_id:'tmd_radar',product_id:'composite_rain_rate',data_state:'radar_estimate',snapshot_id:'latest',fetched_at:'2026-11-04T12:46:00Z',
  source_url:'https://weather.tmd.go.th/composite/index_composite.html',coordinates:[[95,22.5],[108,22.5],[108,4],[95,4]],units:'mm/hour',generation_consistency:'MANIFEST_CLOCK_AND_DOUBLE_IMAGE_HASH_CHECKED_NO_VERSION_TOKEN',frames:[frame]};

describe('Radar contract and immutable image binding',()=>{
  it('accepts original source geometry and validated image hash, never image bytes in metadata',()=>{
    expect(checked.sha256).toBe(createHash('sha256').update(png).digest('hex'));
    const candidate={...feed,frames:[{...checked,observed_at:'2026-11-04T12:30:00Z',path:'zr/24.png',image_base64:png.toString('base64')}]};
    expect(decodedRadarCandidate(candidate,now).feed.frames[0].sha256).toBe(checked.sha256);
    expect(()=>validatedRadar({...feed,frames:[{...frame,image_base64:'unwanted'}]})).toThrow();
  });
  it.each(['url','time','bounds','units','duplicate','oversize','format'])('rejects %s corruption',fault=>{
    const bad=structuredClone(feed);
    if(fault==='url')bad.frames[0].url='https://evil.invalid/x.png';
    if(fault==='time')bad.frames[0].observed_at='2026-02-30T12:45:00Z';
    if(fault==='bounds')bad.coordinates.reverse();
    if(fault==='units')bad.units='mm/24h' as never;
    if(fault==='duplicate')bad.frames.push(frame);
    if(fault==='oversize')bad.frames[0].byte_length=800001;
    if(fault==='format')bad.frames[0].width=1 as never;
    expect(()=>validatedRadar(bad)).toThrow();
  });
  it('distinguishes fresh retrieval from old observations and hides stale/unknown imagery',()=>{
    expect(radarFreshness(feed,now)).toBe('FRESH');
    expect(radarFreshness(feed,now+45*60000)).toBe('DELAYED');
    expect(radarFreshness(feed,now+90*60000)).toBe('STALE');
    expect(radarFreshness(feed,now-600000)).toBe('UNKNOWN');
    expect(radarVisible('STALE')).toBe(false);expect(radarVisible('UNAVAILABLE')).toBe(false);
    expect(radarFreshness(null,now)).toBe('UNAVAILABLE');
  });
  it('counts absent time slots without manufacturing rain values',()=>{
    const older={...frame,observed_at:'2026-11-04T12:00:00Z',url:frame.url.replace('124500','120000')};
    const gap=validatedRadar({...feed,frames:[older,frame]});expect(radarMissingSlots(gap)).toBe(2);
  });
  it('enforces half-hour uploads for legacy captures while preserving gaps and old readable metadata',()=>{
    const candidate={...feed,frames:['11:00','11:15','12:00','12:15','12:30','12:45'].map((time,i)=>({...checked,observed_at:'2026-11-04T'+time+':00Z',path:'zr/'+String(i).padStart(2,'0')+'.png',image_base64:png.toString('base64')}))};
    const sampled=decodedRadarCandidate(candidate,now).feed;
    expect(sampled.sampling_minutes).toBe(30);
    expect(sampled.frames.map(f=>f.observed_at.slice(11,16))).toEqual(['11:00','12:00','12:30']);
    expect(radarMissingSlots(sampled)).toBe(1);
    expect(validatedRadar(feed).frames[0].observed_at).toBe('2026-11-04T12:45:00Z');
    expect(()=>validatedRadar({...feed,sampling_minutes:30})).toThrow();
    expect(()=>decodedRadarCandidate({...candidate,frames:[candidate.frames[1]]},now)).toThrow();
  });
  it('does not freshen a half-hour sample with its newer capture time',()=>{
    const sampled={...feed,frames:[{...frame,observed_at:'2026-11-04T12:30:00Z'}]};
    expect(radarFreshness(sampled,Date.parse('2026-11-04T13:16:00Z'))).toBe('DELAYED');
  });
  it('reports the half-hour cron with its grace period',()=>{
    const result=monitorSource('tmd_radar','FRESH',{status:'SUCCESS',last_attempt:'2026-11-04T12:22:00Z',last_success:'2026-11-04T12:22:00Z'},Date.parse('2026-11-04T12:25:00Z'));
    expect(result.cadence_hours).toBe(.5);expect(result.expected_by).toBe('2026-11-04T13:22:00.000Z');
  });
  it('keeps radar and forecast fills exclusive, including in basin context',()=>{
    expect(effectiveBackground('daily',true,'administrative',true)).toBe('radar');
    expect(effectiveBackground('hourly',true,'basin',true)).toBe('radar');
    expect(backgroundAvailable('radar','2026-11-05','2026-11-04','basin')).toBe(true);
  });
  it('uses provider Mercator placement at three geographic control points',()=>{
    // Independently calculated from provider corners, original 1800×2644 canvas.
    const points=[[100.5018,13.7563,761.78769,1275.21360],[98.9853,18.7883,551.81077,549.23420],[100.4688,7.0084,757.21846,2225.53590]];
    for(const [lon,lat,expectedX,expectedY] of points){const [x,y]=radarControlPixel(lon,lat);expect(x).toBeCloseTo(expectedX,4);expect(y).toBeCloseTo(expectedY,4);}
    expect(radarControlPixel(95,22.5)).toEqual([0,0]);expect(radarControlPixel(108,4)).toEqual([1800,2644]);
  });
  it('rejects corrupted or truncated image bytes before upload',()=>{
    expect(()=>radarPng(png.subarray(0,50))).toThrow();
    const corrupt=Buffer.from(png);corrupt[50]^=1;expect(()=>radarPng(corrupt)).toThrow();
  });
});

describe('Conservative Blob upload reservations',()=>{
  it('reserves migration headroom and charges only new files, not reused images',()=>{
    const first=reserveRadarUploads(undefined,7,now);
    expect(first.reserved).toBe(107);expect(first.remaining).toBe(1693);
    expect(reserveRadarUploads(first.reservations,0,now).reserved).toBe(107);
    expect(reserveRadarUploads(first.reservations,1,now).reserved).toBe(108);
  });
  it('blocks a whole batch before upload, preserves reservations and covers month boundaries',()=>{
    const rows=[{day:'2026-11-04',count:1799}];
    expect(()=>reserveRadarUploads(rows,2,now)).toThrow('budget exhausted');
    expect(rows[0].count).toBe(1799);
    expect(reserveRadarUploads(rows,1,Date.parse('2026-12-01T12:00Z')).reserved).toBe(1800);
    expect(reserveRadarUploads(rows,1,Date.parse('2026-12-05T23:59Z')).reserved).toBe(1800);
    expect(reserveRadarUploads(rows,1,Date.parse('2026-12-06T00:00Z')).reserved).toBe(1);
  });
  it.each([[{day:'2026-02-30',count:1}],[{day:'2026-11-05',count:1}],[{day:'2026-11-04',count:-1}],[{day:'2026-11-04',count:1},{day:'2026-11-04',count:2}]].map(rows=>({rows})))('fails closed on invalid stored reservations %s',({rows})=>{
    expect(()=>reserveRadarUploads(rows,1,now)).toThrow();
  });
});

describe('Scheduled publication authentication',()=>{
  const claims={repository_id:'1433731657',repository:'tordave1150/hazard-intelligence',ref:'refs/heads/main',workflow_ref:'tordave1150/hazard-intelligence/.github/workflows/radar.yml@refs/heads/main',event_name:'workflow_dispatch',runner_environment:'github-hosted',run_id:'1234',run_attempt:'1'};
  let pair:Awaited<ReturnType<typeof generateKeyPair>>;
  beforeAll(async()=>{pair=await generateKeyPair('RS256');});
  const token=async(overrides:Record<string,unknown>={})=>new SignJWT({...claims,...overrides}).setProtectedHeader({alg:'RS256'}).setIssuer('https://token.actions.githubusercontent.com').setAudience('https://hazard-intelligence-lime.vercel.app/api/radar').setIssuedAt().setExpirationTime('5m').sign(pair.privateKey);
  it('accepts a signed short-lived token only for the exact main-branch radar workflow',async()=>{
    const run=await authorizeRadar('Bearer '+await token(),pair.publicKey);expect(run.run_id).toBe('1234');
    await expect(authorizeRadar(null,pair.publicKey)).rejects.toThrow();
  });
  it.each([{repository_id:'another'},{ref:'refs/heads/fork'},{workflow_ref:'tordave1150/hazard-intelligence/.github/workflows/checks.yml@refs/heads/main'},{event_name:'pull_request'},{runner_environment:'self-hosted'}])('rejects untrusted claims %s',async override=>{
    await expect(authorizeRadar('Bearer '+await token(override),pair.publicKey)).rejects.toThrow();
  });
  it('rejects forged signatures and excessive token lifetime',async()=>{
    const other=await generateKeyPair('RS256');await expect(authorizeRadar('Bearer '+await token(),other.publicKey)).rejects.toThrow();
    expect(acceptedRadarClaims({...claims,iat:100,exp:1000})).toBe(false);
  });
});
