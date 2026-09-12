import sys
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.ingestion.imd_history import acquire_year, extract
if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Acquire public IMD annual data without altering any serving source')
    parser.add_argument('--start',type=int,default=2010);parser.add_argument('--end',type=int,default=2024)
    args=parser.parse_args();years=list(range(args.start,args.end+1))
    if not years or len(years)>30:parser.error('Choose 1–30 years per acquisition')
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs={pool.submit(acquire_year,y):y for y in years}
        for job in as_completed(jobs):print(f'{jobs[job]} validated: {job.result()}',flush=True)
    meta=extract(years)
    print({k:v for k,v in meta.items() if k not in ('cells','dates','sources')},flush=True)
