from app.weather import map_rain_level


def test_legacy_probability_does_not_claim_intensity():
    assert map_rain_level(80)=='80-100% chance'
    assert map_rain_level(0)=='0-19% chance'
    assert map_rain_level(None)=='No data'


def test_historical_page_cannot_launch_forecast_etl():
    from pathlib import Path
    source=(Path(__file__).resolve().parents[1]/'app/historical.py').read_text(encoding='utf-8')
    assert 'fetch_weather.py' not in source
    assert 'subprocess.run(' not in source
