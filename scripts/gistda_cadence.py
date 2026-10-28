"""Bounded publication diagnostics. No additional GISTDA HTTP requests.

A provider-version adapter remains disabled until a stable marker is verified.
Publication receipts cannot establish satellite release or acquisition times.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from pipelines.shared.time_units import instant, BANGKOK, utc_now

START = '2026-10-28T00:00:00Z'
END = '2026-11-11T00:00:00Z'
MAX_RECEIPTS = 56


def version_state(previous, marker=None, verified=False):
    if not verified or not marker:
        return 'UNKNOWN_VERSION', None
    digest = hashlib.sha256(marker.encode()).hexdigest()
    return ('FIRST_SEEN_VERIFIED' if previous is None else 'UNCHANGED' if previous == digest else 'CHANGED_VERIFIED'), digest


def receipt(feed, health, checked_at, attempt_after=None):
    if not instant(START) <= instant(checked_at) < instant(END):
        return None
    failed = health.get('status') != 'SUCCESS' or feed is None
    attempt = health.get('completed_at') or health.get('last_attempt') or checked_at
    instant(attempt)
    not_checked = bool(attempt_after and instant(attempt) < instant(attempt_after))
    failed = failed or not_checked
    result = {'check_id': hashlib.sha256((attempt_after or attempt).encode()).hexdigest()[:24], 'source_id': 'gistda',
              'product_window': '1day', 'checked_at': checked_at, 'attempt_at': attempt,
              'query_state': 'NOT_CHECKED' if not_checked else 'FAILED' if failed else 'EMPTY_RESULT' if feed['record_count'] == 0 else 'NONEMPTY_RESULT',
              'version_state': 'UNKNOWN_VERSION', 'provider_published_at': None, 'observed_at': None,
              'response_at': None if failed else feed['response_at'], 'fetched_at': None if failed else feed['fetched_at'],
              'returned_count': None if failed else feed['record_count'], 'complete_query': False if failed else True,
              'scope': 'TH_UNFILTERED', 'evidence': 'PUBLISHED_QUERY_RECEIPT_ONLY'}
    return result


def append_receipt(journal, item):
    if item is None: return journal
    prior = journal.get('receipts', [])
    values = [r for r in prior if r['check_id'] != item['check_id']] + [item]
    values.sort(key=lambda r: instant(r['checked_at']))
    return {'started_at': START, 'ends_at': END, 'extra_provider_checks_enabled': False, 'receipts': values[-MAX_RECEIPTS:]}


def summarize(journal):
    rows = journal.get('receipts', [])
    days = {instant(row['checked_at']).astimezone(BANGKOK).date().isoformat() for row in rows}
    return {'checks': len(rows), 'days_observed': len(days),
            'successes': sum(row['query_state'] in ('EMPTY_RESULT', 'NONEMPTY_RESULT') for row in rows),
            'failures': sum(row['query_state'] == 'FAILED' for row in rows),
            'not_checked': sum(row['query_state'] == 'NOT_CHECKED' for row in rows),
            'unknown_versions': sum(row['version_state'] == 'UNKNOWN_VERSION' for row in rows),
            'verified_changes': sum(row['version_state'] == 'CHANGED_VERIFIED' for row in rows),
            'publication_interval': None, 'publication_hour_recommendation': 'INSUFFICIENT_VERSION_EVIDENCE',
            'trial_start': START, 'trial_end': END, 'schedule': 'EXISTING_DAILY_PUBLICATION_ONLY',
            'gap_note': 'Missing publication days and failed attempts are not proof of no provider release.'}


def main():
    import argparse
    import os
    from pymongo import MongoClient
    from pipelines.gistda.publication import NationalFloodPublisher
    from pipelines.shared.schemas import validate_record
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record-published', action='store_true')
    parser.add_argument('--summary', action='store_true')
    parser.add_argument('--attempt-after', help='UTC start of this publication job; excludes receipts from prior runs')
    args = parser.parse_args()
    if not args.record_published and not args.summary: parser.error('Select --record-published or --summary')
    if args.record_published and not args.attempt_after: parser.error('--record-published requires --attempt-after')
    now = utc_now()
    if args.record_published and not instant(START) <= instant(now) < instant(END):
        print(json.dumps({'monitor': 'TRIAL_INACTIVE', 'extra_provider_checks': False})); return
    try:
        with MongoClient(os.environ['MONGODB_URI'], serverSelectionTimeoutMS=10000) as client:
            db = client[os.getenv('MONGODB_DB_NAME', 'weather_db')]
            store = db.gistda_cadence_trial
            key = 'gistda:1day:2026-10-28'
            journal = store.find_one({'_id': key}) or {}
            if args.record_published:
                rows = NationalFloodPublisher(db).read()
                feed = validate_record('GistdaNationalFloodFeed', rows[0]) if rows else None
                health = db.source_status.find_one({'_id': 'gistda:flood_1day_thailand'}) or {}
                item = receipt(feed, health, now, args.attempt_after)
                journal = append_receipt(journal, item)
                expires = instant(END) + timedelta(days=14)
                store.create_index('expires_at', expireAfterSeconds=0)
                store.replace_one({'_id': key}, {'_id': key, **journal, 'expires_at': expires}, upsert=True)
            print(json.dumps(summarize(journal)))
    except Exception:
        print(json.dumps({'monitor': 'DIAGNOSTIC_UNAVAILABLE', 'extra_provider_checks': False}))
        raise SystemExit(1) from None


if __name__ == '__main__': main()
