import json
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
import pytest
from pipelines.open_meteo.transform import normalize


@pytest.fixture
def payload():
    return {'latitude':13.75,'longitude':100.5,'timezone':'Asia/Bangkok','utc_offset_seconds':25200,
        'daily_units':{'precipitation_sum':'mm','precipitation_probability_max':'%','temperature_2m_max':'°C','temperature_2m_min':'°C'},
        'daily':{'time':['2026-10-25','2026-10-26','2026-10-27','2026-10-28'],
                 'precipitation_sum':[12.5,0,None,2.0],'precipitation_probability_max':[80,0,None,20],
                 'temperature_2m_max':[30,31,None,32],'temperature_2m_min':[24,25,None,26]}}


@pytest.fixture
def area():
    return {'id':'TH-P-10','lat':13.75,'lon':100.5}


@pytest.fixture
def forecast(payload,area):
    return normalize(payload,area,'2026-10-25T01:00:00Z')
