import math
from datetime import date, timedelta
from pipelines.shared.schemas import validate_record
from pipelines.shared.time_units import daily_period, utc_now


def normalize(payload, area, fetched_at):
    if payload.get('timezone') != 'Asia/Bangkok' or payload.get('utc_offset_seconds') != 25200:
        raise ValueError('Unexpected provider timezone')
    daily, units = payload['daily'], payload['daily_units']
    expected_units = {'precipitation_sum': 'mm', 'precipitation_probability_max': '%', 'temperature_2m_max': '°C', 'temperature_2m_min': '°C'}
    if any(units.get(k) != v for k, v in expected_units.items()):
        raise ValueError('Unexpected provider units')
    dates = daily['time']
    if len(dates) != 4 or any(len(daily.get(k, [])) != len(dates) for k in expected_units):
        raise ValueError('Expected four complete forecast periods')
    if dates != [(date.fromisoformat(dates[0]) + timedelta(days=i)).isoformat() for i in range(4)]:
        raise ValueError('Forecast periods must be consecutive')
    from pipelines.shared.time_units import instant, BANGKOK
    if dates[0] != instant(fetched_at).astimezone(BANGKOK).date().isoformat():
        raise ValueError('Provider forecast does not start on retrieval day')
    def value(key, index):
        number = daily[key][index]
        if number is None:
            return None
        if isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number):
            raise ValueError('Non-numeric provider value')
        return number
    periods = []
    for i, day in enumerate(dates):
        start, end = daily_period(day)
        periods.append({'date': day, 'valid_start': start, 'valid_end': end,
            'rainfall_mm': value('precipitation_sum', i), 'rain_probability_pct': value('precipitation_probability_max', i),
            'temp_max_c': value('temperature_2m_max', i), 'temp_min_c': value('temperature_2m_min', i)})
    if all(p['rainfall_mm'] is None and p['rain_probability_pct'] is None for p in periods):
        raise ValueError('Entirely missing forecast rejected')
    record = {'schema_version': '2.0', 'source_id': 'open_meteo', 'product_id': 'daily_forecast',
        'location_id': area['id'], 'data_state': 'forecast', 'forecast_reference_time': None,
        'fetched_at': fetched_at, 'ingested_at': utc_now(), 'valid_periods': periods,
        'point': {'lat': area['lat'], 'lon': area['lon']},
        'model_point': {'lat': payload['latitude'], 'lon': payload['longitude']},
        'spatial_method': 'Representative interior point; model grid forecast, not an area average',
        'quality_status': 'partial' if any(p['rainfall_mm'] is None or p['rain_probability_pct'] is None for p in periods) else 'valid',
        'units': {'rainfall': 'mm/24h', 'probability': '%', 'temperature': '°C'},
        'source_url': 'https://open-meteo.com/en/docs'}
    return validate_record('Forecast', record)
