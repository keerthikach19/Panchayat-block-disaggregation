"""Render measured NWP results from the frozen evaluation without manual transcription."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.ingestion.forecast_schema import ROOT,read_json,file_hash


def main():
    base=ROOT/'data/research/benchmarks';pointer=read_json(base/'nwp_evidence.json')
    # The explanatory prose below describes this one frozen audit, not future runs.
    if pointer != {'experiment_id':'nwp-model-badc5a9e1eb18c3ff1b4','evaluation_id':'evaluation-2b37883a3571e9ee'}:
        raise ValueError('This written interpretation belongs to the September 2026 frozen audit')
    directory=base/pointer['experiment_id']/pointer['evaluation_id']
    for name,expected in read_json(directory/'artifact_hashes.json').items():
        if file_hash(directory/name)!=expected:raise ValueError('Evaluation checksum mismatch')
    report=read_json(directory/'report.json');rows=report['by_lead']
    pct=lambda x:f'{100*x:.1f}%'
    lines=['# Forecast-informed rainfall: measured results','',
      '**The joint 50% detection / 50% precision target was not achieved at any lead.**',
      'The frozen choices improve event CSI over uncorrected GFS on leads 2–5, while lead 1 is worse.',
      'Most observed ≥20 mm cases are still missed. Four leads have precision above 50%; lead 4 does not.',
      'These results support a narrower claim of useful forecast information and some calibration gains, not validated village forecasting.','',
      'Final audit: 22 Nashik grid centers × 34 sampled initialization dates = **748 cases per lead**,',
      'with no missing pairs. Target dates span June 2–September 13, 2026 across the five leads.',
      '2026 IMD observations are provisional. Models, calibrations and thresholds were selected without Nashik',
      'labels and frozen before this audit. See [method and reproducibility](../NWP_RAINFALL_MODEL.md).','',
      '## Event alerts','',
      '| Lead | Detection | Precision | Hits / observed | Misses | False / alerts | CSI |',
      '|---|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        e=r['event'];lines.append(f"| {r['lead_days']} | {pct(e['recall'])} | {pct(e['precision'])} | {e['hits']} / {e['observed_events']} | {e['misses']} | {e['false_alarms']} / {e['alerts']} | {e['csi']:.3f} |")
    lines += ['', 'Detection = hits / actual ≥20 mm cases. Precision = hits / alerts. Neither is an overall',
      'rainfall “accuracy percentage.” CSI = hits / (hits + misses + false alarms).',
      'For example, lead 1 correctly alerts for 39 of 95 events, misses 56, and issues 6 false alerts.',
      'Its 86.7% precision therefore does **not** mean it catches 86.7% of events.','',
      '## Same-case comparison with uncorrected GFS','',
      '| Lead | GFS → selected detection | GFS → selected precision | GFS → selected CSI |',
      '|---|---:|---:|---:|']
    for r in rows:
        a,b=r['raw_event'],r['event'];lines.append(f"| {r['lead_days']} | {pct(a['recall'])} → {pct(b['recall'])} | {pct(a['precision'])} → {pct(b['precision'])} | {a['csi']:.3f} → {b['csi']:.3f} |")
    lines += ['', 'The earlier rainfall-history model was tested on 2025, so its numbers cannot establish a',
      'controlled before/after improvement against these 2026 scores. Uncorrected GFS is the',
      'matched baseline here. High precision on this sample is partly present in that baseline already.',
      'The strongest event gain is lead 2: 13 → 37 hits with false alerts increasing from 4 to 8.',
      'Lead 4 catches more events but produces substantially more false alerts. Lead 5 gains little in CSI.',
      'These comparisons are descriptive; broad uncertainty prevents a claim of universal improvement.','',
      '## Rainfall amounts','',
      'All errors are in mm. Lower MAE/RMSE is better; bias closer to zero is better.',
      'An event alert does not change the numeric amount estimate.','',
      '| Lead | MAE: GFS → selected | RMSE: GFS → selected | Bias: GFS → selected | Amount-based ≥20 mm detection |',
      '|---|---:|---:|---:|---:|']
    for r in rows:
        a,b=r['raw_amount'],r['amount'];lines.append(f"| {r['lead_days']} | {a['mae_mm']:.2f} → {b['mae_mm']:.2f} | {a['rmse_mm']:.2f} → {b['rmse_mm']:.2f} | {a['bias_mm']:.2f} → {b['bias_mm']:.2f} | {pct(b['event_at_20mm']['recall'])} |")
    lines += ['', 'Amount MAE and RMSE improve on leads 1, 2 and 5; leads 3 and 4 retain raw GFS.',
      'Underprediction remains substantial. Bias worsens on leads 1 and 5 despite lower MAE/RMSE.',
      'The validation constraints did not guarantee the same behavior in Nashik 2026.','',
      '## Uncertainty and frozen choices','',
      '| Lead | Detection: approximate 95% interval | Precision: approximate 95% interval | Event model | Probability threshold |',
      '|---|---:|---:|---|---:|']
    for r,c in zip(rows,report['selection']['by_lead']):
        ci=r['event_intervals_95'];model=r['selected_event']
        threshold=pct(c['event_candidates'][model]['selection']['threshold']) if model!='raw_gfs' else 'GFS ≥20 mm'
        lines.append(f"| {r['lead_days']} | {'–'.join(map(pct,ci['recall']))} | {'–'.join(map(pct,ci['precision']))} | {model} | {threshold} |")
    lines += ['', 'Intervals use a circular bootstrap of two adjacent initialization dates, preserving all',
      'cells within each date (500 replicates, fixed seed). They are wide: only 34 initialization dates',
      'and one partial season are available. Do not interpret an interval crossing 50% as passing the target.',
      'None of the five leads met all joint event constraints on the 2025 selection set either.','',
      'The new approach supplies future atmospheric forecasts instead of only rainfall history, and',
      'selects alerts separately from amount error. The same-case GFS comparison measures the added',
      'value of the statistical correction. It does not isolate a causal benefit from every individual feature.',
      'Improvement remains limited by the small sampled archive, geographic/year shift, storm-location',
      'and timing errors in the forecast, and coarse/provisional target data; this experiment does not',
      'measure the contribution of each limitation separately.','',
      '## Release and verification','',
      'No village-serving forecast or official IMD block input was replaced. The app presents this as',
      'research evidence and explains detection, precision, false alerts and amount errors separately.',
      'The saved-prediction test recomputes all reported metrics and frozen threshold decisions.',
      'Timing, missing steps, date receipts, geographic exclusions and API evidence identity are tested.',
      'An initial evaluator date-label reduction was corrected before the report was generated;',
      'no fitted model, calibration coefficient or selected threshold changed.','',
      f"Experiment: `{report['experiment_id']}`  ",f"Evaluation: `{report['evaluation_id']}`  ",
      f"Selection frozen: `{report['selection']['frozen_at']}`  ",
      f"Selection SHA-256: `{report['selection_sha256']}`",'',
      'Sources: [NOAA GFS processed by dynamical.org, CC BY 4.0](https://dynamical.org/catalog/noaa-gfs-forecast/)',
      'and [IMD daily provisional rainfall](https://imdpune.gov.in/cmpg/Realtimedata/Rainfall/Rain_Download.html).',
      'Archive snapshot, observation receipts, checksums, candidate scores and prediction arrays accompany the experiment.','']
    path=ROOT/'docs/reports/nwp-rainfall-results.md';path.write_text('\n'.join(lines),encoding='utf-8');print(path)


if __name__=='__main__':main()
