"""Read-only source acceptance evidence. Never publishes or uploads forecast images."""
import argparse
import hashlib
import json
import re
from datetime import datetime,timezone
from pathlib import Path
import requests

SOUTH='https://satda.tmd.go.th/wp-content/uploads/data/dashboard/radar_map/'
URLS={'south_viewer':SOUTH+'south_nowcast.php','south_manifest':SOUTH+'leaflet_layers/layers.json',
      'bangkok_manifest':'https://satda.tmd.go.th/wp-content/uploads/nowcasting/bkk/bangkok_frames/manifest.json',
      'khon_kaen_viewer':'https://satda.tmd.go.th/wp-content/uploads/nowcasting/kkn/khon_kaen.php'}


def inspect_south(manifest,viewer,now):
    """Filename UTC is explicit in the source viewer; issue/generated clocks are not."""
    issues=[]
    compact=re.sub(r'\s+','',viewer)
    convention=bool(re.search(r'functionparseUTC\(fname\)\{.{0,400}?newDate\(Date.UTC\(m\[1\],m\[2\]-1,m\[3\],m\[4\],m\[5\]\)\)',compact)) and 'date:parseUTC(l.name)' in compact
    if not convention:issues.append('SOURCE_UTC_CONVENTION_CHANGED')
    if not isinstance(manifest,dict):return {'state':'NOT_ACCEPTED','issues':['INVALID_MANIFEST']}
    frames=manifest.get('frames')
    if not isinstance(frames,list) or not 1<=len(frames)<=40:return {'state':'NOT_ACCEPTED','issues':['INVALID_FRAME_COUNT']}
    times=[];names=[];kinds=[]
    for frame in frames:
        try:
            name=frame['name']
            if not re.fullmatch(r'\d{12}\.png',name):raise ValueError()
            stamp=datetime.strptime(name,'%Y%m%d%H%M.png').replace(tzinfo=timezone.utc)
            if stamp.minute%15 or frame['dt']!=stamp.strftime('%Y-%m-%dT%H:%M:%S') or frame['kind'] not in ['observ','swirls']:raise ValueError()
            times.append(stamp);names.append(name);kinds.append(frame['kind'])
        except (KeyError,TypeError,ValueError):issues.append('INVALID_FRAME_ENTRY')
    if len(names)!=len(set(names)):issues.append('DUPLICATE_FRAME_NAME')
    if any(a>=b for a,b in zip(times,times[1:])):issues.append('NON_INCREASING_VALID_TIMES')
    index=manifest.get('now_index');base=None
    if len(times)==len(frames) and type(index) is int and 0<=index<len(times) and kinds[index]=='observ':
        base=times[index]
        if manifest.get('base_time')!=base.strftime('%Y-%m-%dT%H:%M:%S'):issues.append('BASE_TIME_DISAGREES')
        if kinds[:index+1]!=['observ']*(index+1) or any(k!='swirls' for k in kinds[index+1:]):issues.append('OBSERVATION_FORECAST_ORDER_INVALID')
        leads=[int((t-base).total_seconds()/60) for t,k in zip(times,kinds) if k=='swirls']
        if any(t<=0 or t>180 for t in leads):issues.append('FORECAST_OUTSIDE_ADVERTISED_180_MINUTES')
        if convention and (now-base).total_seconds()>5400:issues.append('BASE_OBSERVATION_STALE')
        if convention and (base-now).total_seconds()>300:issues.append('BASE_OBSERVATION_IN_FUTURE')
    else:issues.append('INVALID_NOW_INDEX')
    if manifest.get('total_frames')!=len(frames) or manifest.get('obs_count')!=kinds.count('observ') or manifest.get('fc_count')!=kinds.count('swirls'):issues.append('FRAME_COUNTS_DISAGREE')
    # Source display bounds and dBZ legend do not certify a numerical grid or valid pixels.
    issues+=['ISSUE_TIME_NOT_QUALIFIED','NATIONAL_VALID_COVERAGE_NOT_ESTABLISHED','IMAGE_REUSE_AND_FORECAST_STORAGE_BUDGET_NOT_ACCEPTED']
    return {'state':'NOT_ACCEPTED','source_url':URLS['south_manifest'],'viewer_url':URLS['south_viewer'],
        'valid_time_convention':'UTC_FROM_SOURCE_FILENAME_PARSER' if convention else 'UNKNOWN',
        'base_observation_utc':base.isoformat().replace('+00:00','Z') if base and convention else None,
        'issued_at_utc':None,'generated_at_raw':manifest.get('generated_at'),'display_units':'dBZ' if 'dBZ' in viewer else 'UNKNOWN',
        'frame_count':len(frames),'observation_count':kinds.count('observ'),'forecast_count':kinds.count('swirls'),
        'forecast_leads_minutes':[int((t-base).total_seconds()/60) for t,k in zip(times,kinds) if k=='swirls'] if base else [],
        'duplicate_frame_names':sorted({n for n in names if names.count(n)>1}),
        'image_bounds_raw':frames[0].get('bounds') if isinstance(frames[0],dict) else None,'issues':list(dict.fromkeys(issues))}


def fetch_text(url):
    with requests.get(url,timeout=(10,20),stream=True,allow_redirects=False,headers={'User-Agent':'HazardIntelligence/1.0 (read-only source review)'}) as response:
        if response.status_code!=200:raise ValueError('Source response unavailable')
        data=bytearray()
        for chunk in response.iter_content(8192):
            data.extend(chunk)
            if len(data)>200000:raise ValueError('Source evidence byte budget exceeded')
        return bytes(data)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--export',type=Path);args=parser.parse_args()
    now=datetime.now(timezone.utc);documents={};evidence={}
    for name,url in URLS.items():
        try:
            data=fetch_text(url);documents[name]=data.decode('utf-8');evidence[name]={'url':url,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
        except (requests.RequestException,UnicodeError,ValueError) as exc:evidence[name]={'url':url,'error_type':type(exc).__name__}
    report={'reviewed_at':now.isoformat().replace('+00:00','Z'),'state':'NOT_ACCEPTED','publishes_images':False,'evidence':evidence}
    if 'south_manifest' in documents and 'south_viewer' in documents:
        try:report['south']=inspect_south(json.loads(documents['south_manifest']),documents['south_viewer'],now)
        except ValueError:report['south']={'state':'NOT_ACCEPTED','issues':['INVALID_JSON']}
    if 'bangkok_manifest' in documents:
        try:
            mf=json.loads(documents['bangkok_manifest']);generated=datetime.fromisoformat(mf['generated_at'].replace('Z','+00:00'))
            report['bangkok']={'state':'NOT_ACCEPTED','generated_at_raw':mf['generated_at'],'stale':generated.utcoffset() is None or (now-generated).total_seconds()>5400,
                'field':mf.get('field'),'issues':['THIRD_PARTY_REUSE_NOT_ACCEPTED','NOT_A_NATIONAL_PRODUCT']}
        except (ValueError,KeyError,TypeError):report['bangkok']={'state':'NOT_ACCEPTED','issues':['INVALID_MANIFEST']}
    if 'khon_kaen_viewer' in documents:
        files=sorted(set(re.findall(r'(\d{8}_\d{6})\.png',documents['khon_kaen_viewer'])))
        report['khon_kaen']={'state':'NOT_ACCEPTED','frame_times_raw':files,'timezone':'UNKNOWN','issues':['TIMEZONE_AND_ISSUE_TIME_NOT_QUALIFIED','NOT_A_NATIONAL_PRODUCT']}
    output=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    if args.export:
        args.export.parent.mkdir(parents=True,exist_ok=True);args.export.write_text(output,encoding='utf-8')
    print(output)


if __name__=='__main__':main()
