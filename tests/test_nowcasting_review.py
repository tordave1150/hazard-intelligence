from copy import deepcopy
from datetime import datetime,timezone
import pytest
from scripts.inspect_nowcasting import inspect_south

VIEWER="""function parseUTC(fname){const m=fname.match(/unused/);return new Date(Date.UTC(m[1],m[2]-1,m[3],m[4],m[5]));} meta=list.map(l=>({date:parseUTC(l.name)})); dBZ"""
NOW=datetime(2026,11,4,14,45,tzinfo=timezone.utc)


def manifest():
    return {'generated_at':'2026-11-04T21:39:00','base_time':'2026-11-04T14:00:00','now_index':0,'total_frames':3,'obs_count':1,'fc_count':2,
        'frames':[{'name':'20261104'+time+'.png','dt':'2026-11-04T'+time[:2]+':'+time[2:]+':00','kind':kind,'bounds':[[4,96],[22,107]]} for time,kind in [('1400','observ'),('1430','swirls'),('1500','swirls')]]}


def test_utc_valid_times_are_qualified_but_never_invent_issue_time_from_generated_wall_clock():
    result=inspect_south(manifest(),VIEWER,NOW)
    assert result['valid_time_convention']=='UTC_FROM_SOURCE_FILENAME_PARSER'
    assert result['base_observation_utc']=='2026-11-04T14:00:00Z'
    assert result['generated_at_raw']=='2026-11-04T21:39:00'
    assert result['issued_at_utc'] is None and result['state']=='NOT_ACCEPTED'
    assert result['display_units']=='dBZ' and result['forecast_leads_minutes']==[30,60]
    assert result['coverage_scope']=='REGIONAL'
    assert 'VALID_COVERAGE_AND_NO_DATA_NOT_QUALIFIED' in result['issues']


def test_duplicate_and_out_of_horizon_frames_block_the_entire_source_without_silent_repair():
    mf=manifest();mf['frames'][-1].update(name='202611042145.png',dt='2026-11-04T21:45:00');mf['frames'].append(deepcopy(mf['frames'][-1]));mf.update(total_frames=4,fc_count=3)
    result=inspect_south(mf,VIEWER,NOW)
    assert result['duplicate_frame_names']==['202611042145.png']
    assert result['forecast_leads_minutes']==[30,465,465]
    assert {'DUPLICATE_FRAME_NAME','NON_INCREASING_VALID_TIMES','FORECAST_OUTSIDE_ADVERTISED_180_MINUTES'}<=set(result['issues'])


@pytest.mark.parametrize('fault',['parser','filename','dt','now_index','counts','stale'])
def test_source_changes_and_unusable_frames_fail_acceptance(fault):
    mf=manifest();viewer=VIEWER;now=NOW
    if fault=='parser':viewer=viewer.replace('Date.UTC','Date.local')
    elif fault=='filename':mf['frames'][0]['name']='../../other.png'
    elif fault=='dt':mf['frames'][0]['dt']='2026-11-04T14:15:00'
    elif fault=='now_index':mf['now_index']=100
    elif fault=='counts':mf['obs_count']=9
    elif fault=='stale':now=datetime(2026,11,5,tzinfo=timezone.utc)
    result=inspect_south(mf,viewer,now)
    expected={'parser':'SOURCE_UTC_CONVENTION_CHANGED','filename':'INVALID_FRAME_ENTRY','dt':'INVALID_FRAME_ENTRY','now_index':'INVALID_NOW_INDEX','counts':'FRAME_COUNTS_DISAGREE','stale':'BASE_OBSERVATION_STALE'}[fault]
    assert expected in result['issues'] and result['state']=='NOT_ACCEPTED'
