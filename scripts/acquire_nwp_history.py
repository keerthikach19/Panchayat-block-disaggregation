"""Download resumable regional GFS subsets and provisional 2026 IMD observations."""
import argparse
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
import numpy as np
from src.ingestion.forecast_schema import ROOT, read_json, immutable_json, file_hash
from src.ingestion.nwp_archive import experiment_context, initialization_dates, open_gfs, acquire_gfs_run, acquire_daily, decode_daily


def main(kind, workers):
    config, meta, version = experiment_context()
    if kind == 'gfs':
        dates = initialization_dates(config).append(initialization_dates(config, fresh=True))
        ds = open_gfs(config)
        directory = ROOT/'data/research/raw/gfs'/version
        directory.mkdir(parents=True, exist_ok=True)
        def acquire(day):
            for attempt in range(3):
                try: return acquire_gfs_run(ds, day, config, meta['cells'], directory)
                except Exception:
                    if attempt == 2: raise
                    time.sleep(2*(attempt+1))
    else:
        dates = sorted({d + pd.Timedelta(days=lead+1) for d in initialization_dates(config, fresh=True) for lead in config['lead_days']})
        def acquire(day):
            for attempt in range(3):
                try: return acquire_daily(day)
                except Exception:
                    if attempt == 2: raise
                    time.sleep(2*(attempt+1))
    failures, paths = [], []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        jobs = {pool.submit(acquire, d): d for d in dates}
        for completed, job in enumerate(as_completed(jobs), 1):
            day = jobs[job]
            try: paths.append(job.result()); print(f'{kind} {completed}/{len(dates)} {day:%Y-%m-%d} OK', flush=True)
            except Exception as exc: failures.append(dict(date=str(day), error=str(exc))); print(f'{kind} {day} FAILED: {exc}', flush=True)
    if failures: raise RuntimeError(f'Acquisition incomplete: {failures}')
    if kind == 'observations':
        paths.sort()
        arrays = [decode_daily(p.read_bytes())[:, :] for p in paths]
        values = np.stack([a[[c['iy'] for c in meta['cells']], [c['ix'] for c in meta['cells']]] for a in arrays])
        out = ROOT/'data/research/arrays'/version; out.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(out/'observations-2026.npz', dates=np.array([p.stem for p in paths],dtype='U10'), rainfall=values)
        immutable_json(ROOT/'data/research/manifests'/f'{version}-observations.json', dict(
            dataset_version=version, source='IMD real-time daily gauge grid', provisional=True,
            array_sha256=file_hash(out/'observations-2026.npz'), cells=meta['cells'],
            source_records=[read_json(p.with_suffix('.json')) for p in paths]))
    print(f'COMPLETE {kind}: {version}', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--kind', choices=['gfs','observations'], required=True)
    p.add_argument('--workers', type=int, default=4)
    args = p.parse_args()
    if not 1 <= args.workers <= 4: p.error('Use 1–4 workers')
    main(args.kind, args.workers)
