"""Small, public-safe provenance for scheduled collection health."""
import os
import re


def workflow_context():
    repository = os.getenv('GITHUB_REPOSITORY', '')
    run_id = os.getenv('GITHUB_RUN_ID', '')
    event = os.getenv('GITHUB_EVENT_NAME', '')
    result = {}
    if re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository) and re.fullmatch(r'[0-9]+', run_id):
        result['run_url'] = f'https://github.com/{repository}/actions/runs/{run_id}'
    if event in {'schedule', 'workflow_dispatch', 'push'}:
        result['run_trigger'] = event
    return result


def start_run(db, key, status):
    status.update(status='RUNNING', **workflow_context())
    if db is not None:
        db.source_status.update_one({'_id': key}, {'$set': status,
            '$unset': {'completed_at': '', 'error_summary': '', 'error_stage': '', 'http_status': ''}}, upsert=True)
