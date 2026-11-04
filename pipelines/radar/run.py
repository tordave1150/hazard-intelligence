"""Capture source images; export locally or publish through the scoped OIDC receiver."""
import argparse
import json
import os
import time
from pathlib import Path
import requests
from .client import capture

PUBLISH_URL='https://hazard-intelligence-lime.vercel.app/api/radar'


def publish(payload):
    token_url=os.environ['ACTIONS_ID_TOKEN_REQUEST_URL']
    token=requests.get(token_url,params={'audience':PUBLISH_URL},headers={'Authorization':'Bearer '+os.environ['ACTIONS_ID_TOKEN_REQUEST_TOKEN']},timeout=20).json()['value']
    response=requests.post(PUBLISH_URL,json=payload,headers={'Authorization':'Bearer '+token},timeout=240,allow_redirects=False)
    if response.status_code!=200:raise RuntimeError(f'Radar publication returned HTTP {response.status_code}')
    result=response.json()
    if result.get('status') not in ['SUCCESS','ALREADY_PUBLISHED']:raise RuntimeError('Radar publication was not completed')
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--export',type=Path);parser.add_argument('--publish',action='store_true');args=parser.parse_args()
    if not args.export and not args.publish:parser.error('Select --export and/or --publish')
    try:
        if args.publish:
            # A code push can start Actions before its Vercel deployment is ready.
            for attempt in range(30):
                try:
                    response=requests.get(PUBLISH_URL,timeout=10)
                    if response.status_code==200 and response.json().get('deployment_commit')==os.environ.get('GITHUB_SHA'):break
                except requests.RequestException:pass
                if attempt==29:raise RuntimeError('Matching production receiver not ready')
                time.sleep(5)
        payload=capture()
        if args.export:
            args.export.parent.mkdir(parents=True,exist_ok=True)
            temporary=args.export.with_suffix('.tmp');temporary.write_text(json.dumps(payload,separators=(',',':')),encoding='utf-8');os.replace(temporary,args.export)
        if args.publish:
            result=publish(payload);print(json.dumps({'source_id':'tmd_radar','status':result.get('status'),'frame_count':result.get('frame_count')}))
        else:print(json.dumps({'source_id':'tmd_radar','status':'CAPTURED','frames':len(payload['frames'])}))
    except Exception as exc:
        if args.publish:
            try:publish({'capture_failed':True})
            except Exception:pass
        print(json.dumps({'source_id':'tmd_radar','status':'FAILED','error_type':type(exc).__name__}));raise RuntimeError('Radar capture/publication failed; previous generation retained') from None


if __name__=='__main__':main()
