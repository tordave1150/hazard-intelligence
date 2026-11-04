import re
from datetime import datetime
from pipelines.shared.publication import Publisher
from pipelines.shared.schemas import validate_record


def check_envelope(records,expected_ids):
    if expected_ids!=['latest'] or len(records)!=1:raise ValueError('One radar envelope required')
    feed=records[0];validate_record('RadarManifest',feed)
    frames=feed['frames'];times=[datetime.fromisoformat(f['observed_at'].replace('Z','+00:00')).timestamp() for f in frames]
    fetched=datetime.fromisoformat(feed['fetched_at'].replace('Z','+00:00')).timestamp()
    if times!=sorted(set(times)) or times[-1]-times[0]>10800 or any(t%(feed.get('sampling_minutes',15)*60) or t>fetched+300 for t in times):raise ValueError('Invalid radar times')
    if sum(f['byte_length'] for f in frames)>2800000:raise ValueError('Radar byte budget exceeded')
    for f in frames:
        leaf=f['observed_at'].replace('-','').replace(':','')+'-'+f['sha256']+'.png'
        if not re.fullmatch(r'https://[a-z0-9]+\.public\.blob\.vercel-storage\.com/tmd-radar/'+re.escape(leaf),f['url']):raise ValueError('Untrusted radar URL')
    if len({f['url'] for f in frames})!=len(frames):raise ValueError('Duplicate radar objects')
    return {'requested_locations':1,'successful_locations':1,'completeness':1,'frame_count':len(frames)}


class RadarPublisher(Publisher):
    collection_name='radar_latest'
    identity_field='snapshot_id'
    schema_name='RadarManifest'

    def validate(self,records,expected_ids):return check_envelope(records,expected_ids)
    def read(self,source='tmd_radar',product='composite_rain_rate'):return super().read(source,product)
    def rollback(self,source='tmd_radar',product='composite_rain_rate'):return super().rollback(source,product)
