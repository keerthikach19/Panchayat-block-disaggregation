"""Report actual usable evidence; date-only source records are never silently paired."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.ingestion.forecast_schema import ROOT, read_json, immutable_json, digest

def audit():
    active=read_json(ROOT/'data/imported/block_forecasts/nashik/active.json')
    source_dir=ROOT/'data/imported/block_forecasts/nashik'/active['dataset_version']
    blocks=read_json(source_dir/'forecasts.json')
    comparison=read_json(ROOT/'docs/reports/comparison-1ba7a9427fa1b01026b3.json')
    district=comparison['district_bulletin_snapshot']
    manifests=[read_json(p) for p in sorted((ROOT/'data/research/manifests').glob('imd-20*.json'))]
    report={'status':'NOT_READY_FOR_OFFICIAL_FORECAST_CALIBRATION',
      'preserved_fallback_commit':'49ea992048522dcb389a2a1fbb6d171fa7be24b0',
      'block_source_records':len(blocks),'block_issue_dates':sorted({r['issue_date'] for r in blocks}),
      'district_issue_dates':[district['issued_date']],'district_source_records':len(district['forecast_days']),
      'historical_observation_years':[r['year'] for r in manifests],
      'exact_issued_forecast_observation_pairs':0,
      'blockers':['Existing block and district exports have issue dates, not verified issue timestamps.',
        'Exact rainfall accumulation intervals and geographic support of parent inputs are unverified.',
        'Historical IMD analyses end in 2024 for this experiment; preserved source forecasts are in 2026.',
        'Legacy station-labelled CSV is NASA POWER proxy data, not an independently verified gauge archive.',
        'No authenticated historical paired IMD forecast archive or independent Nashik gauge observations has been acquired.'],
      'next_data_contract':{'forecast_required':['source','source_sha256','location_id','support_id','issued_at','available_at','valid_start','valid_end','rainfall_mm'],
        'observation_required':['source_sha256','location_id','support_id','valid_start','valid_end','rainfall_mm','target_kind'],
        'feature_required':['name','value','available_at']},
      'allowed_now':['Retrospective grid-level lagged rainfall benchmark with spatial and temporal holdouts',
        'Test interval alignment and reconciliation on explicitly labelled software fixtures'],
      'not_allowed':['Production activation','Claiming village forecast skill','Fabricating past issued forecasts from observed rainfall','Forcing source agreement to a preset maximum difference']}
    identity='readiness-'+digest(report)[:20]
    out=ROOT/'data/research/audits'/f'{identity}.json';immutable_json(out,report)
    print(out)
    print(report['status'])
    return report
if __name__=='__main__':audit()
