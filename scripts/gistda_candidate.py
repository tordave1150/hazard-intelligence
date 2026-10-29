"""Receipt-only entry point for the complete three-day Thailand candidate.

No database writes, district filters or raw geometry output.
"""
import json
import os
from scripts.gistda_common import CandidateError
from scripts.gistda_national import collect_national_candidate


def main():
    try:
        candidate=collect_national_candidate(os.getenv('GISTDA_API_KEY',''),three_day=True)
        report={key:candidate[key] for key in ('source_id','product_id','product_window','area_id',
            'record_count','page_count','observed_at','complete_provider_query','fetched_at')}
        print(json.dumps({'status':'CANDIDATE_VALIDATED',**report},allow_nan=False))
    except Exception as error:
        reason=error.reason if isinstance(error,CandidateError) else 'CANDIDATE_FAILED'
        print(json.dumps({'source_id':'gistda','status':'FAILED','reason':reason}))
        raise SystemExit(1) from None


if __name__=='__main__':
    import argparse
    argparse.ArgumentParser(description=__doc__).parse_args()
    main()
