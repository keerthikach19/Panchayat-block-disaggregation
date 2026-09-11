"""Freeze the locally cached district bulletin and report paired disagreement."""
import sys
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.ingestion.forecast_schema import ROOT, read_json, immutable_json
from src.ingestion.imd_live import IMDLiveData
from src.services.forecast_service import ForecastService
from src.services.comparison import ComparisonService, statistics

def generate():
    cache=read_json(ROOT/'data/cache/district_forecasts/agromet_nashik.json')
    live=Mock()
    live.fetch_forecast.return_value=IMDLiveData.select_forecast(cache,cached=True)
    comparison=ComparisonService(ForecastService(live=live))
    first=comparison.compare()
    reports=[comparison.compare(valid_date=day, block_run_id=first['block_source']['run_id'],
             district_run_id=first['district_source']['run_id']) for day in first['overlap_dates']]
    rows=[r for report in reports for r in report['rows']]
    aggregate=statistics(rows)
    folder=ROOT/'docs/reports'
    folder.mkdir(exist_ok=True)
    identity=first['comparison_id']
    immutable_json(folder/(identity+'.json'),{'district_bulletin_snapshot':cache,'reports':reports,'aggregate':aggregate})
    f=lambda x:f'{x:.2f}'
    lines=['# Same-day block-to-village versus district-to-village comparison',
      '',f"Snapshot: `{identity}`. Prepared from the local IMD bulletin downloaded {cache['fetched_at']}.",
      '', '## What is being compared', '',
      f"Block issue **{first['block_source']['issue_date']}** versus district issue **{first['district_source']['issue_date']}**. Shared forecast dates: **{', '.join(first['overlap_dates'])}**.",
      '',f"Each date pairs {first['summary']['count']:,} villages by exact ID, parent and valid date. Across {len(reports)} dates there are {len(rows):,} village-date pairs. These are repeated forecasts, not independent observations.",
      '',f"Block-only dates: {', '.join(first['block_only_dates']) or 'none'}. District-only dates: {', '.join(first['district_only_dates']) or 'none'}. Dates outside the intersection are excluded; none are shifted or interpolated.",
      '', 'Only rainfall can be compared. The district adapter currently extracts rainfall only; temperature, humidity, cloud and wind are missing on that path. This is a software extraction limitation, not proof that IMD never publishes them. The unit is mm for the source-labelled day; identical accumulation hours are not verified.',
      '', 'The geography consists of village polygons, not verified gram-panchayat boundaries. All 15 mapped blocks are represented. The 37 unresolved Central features are excluded from numerical pairs; no missing parent is guessed.',
      '', '## Main findings', '',
      f"Across all pairs, mean absolute disagreement is **{f(aggregate['mean_absolute_difference_mm'])} mm**, root-mean-square disagreement is **{f(aggregate['root_mean_square_difference_mm'])} mm**, and the largest absolute gap is **{f(aggregate['max_absolute_difference_mm'])} mm**.",
      '',f"Block-derived forecasts are higher in {aggregate['block_higher']:,} pairs; district-derived forecasts are higher in {aggregate['district_higher']:,}; {aggregate['equal_within_rounding']:,} agree within 0.0001 mm. {aggregate['above_5mm']:,} pairs ({100*aggregate['above_5mm']/len(rows):.1f}%) differ by more than 5 mm, and {aggregate['above_10mm']:,} ({100*aggregate['above_10mm']/len(rows):.1f}%) differ by more than 10 mm.",
      '', 'These numbers measure disagreement, not forecast error. Neither route can be declared more accurate without independent observed rainfall.',
      '', '## Date-by-date results', '',
      'All means in the first table give each village equal weight. Difference = block-derived minus district-derived; a negative value means the district route is wetter.', '',
      '| Valid date | District source | Block local mean | District local mean | Signed mean gap | Mean absolute gap | RMS gap | Median absolute gap | P90 absolute gap | Maximum absolute gap |',
      '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in reports:
        s=r['summary']
        lines.append('| '+r['valid_date']+' | '+ ' | '.join(f(v) for v in [r['rows'][0]['district_source_mm'],s['block_mean_mm'],s['district_mean_mm'],s['mean_difference_mm'],s['mean_absolute_difference_mm'],s['root_mean_square_difference_mm'],s['median_absolute_difference_mm'],s['p90_absolute_difference_mm'],s['max_absolute_difference_mm']])+' |')
    lines += ['', '### Area-weighted view', '',
      'Large villages contribute more here. Weights are geodesic areas of the same matched footprints, not population or crop area. District means conserve the district source only across its full modeled footprint; missing pairs would invalidate that equality.', '',
      '| Date | Area-weighted block | Area-weighted district | Signed gap | Mean absolute gap |', '|---|---:|---:|---:|---:|']
    for r in reports:
        s=r['summary'];lines.append('| '+r['valid_date']+' | '+' | '.join(f(s[k]) for k in ['area_weighted_block_mm','area_weighted_district_mm','area_weighted_difference_mm','area_weighted_absolute_difference_mm'])+' |')
    lines += ['', '## Why identical terrain and dates do not imply identical forecasts', '',
      '### 1. The parent inputs differ', '',
      'The block path starts with a forecast specific to each block, while the district path starts with one district-wide number. The local adjustment does not replace this input. Different inputs therefore produce different village outputs even with an unchanged model and terrain.', '',
      '### 2. The forecasts were issued on different days', '',
      f"The district issue is {first['district_issue_days_later']} calendar day later. For example, for 13 September the block issue is three calendar days earlier and the district issue is two days earlier. Exact lead hours are unknown. The comparison combines source-resolution differences with a forecast-update difference; those two influences cannot be separated from this pair of bulletins.", '',
      'Weather forecasts depend on atmospheric conditions, not just terrain. New observations can alter initial conditions and subsequent forecasts. This is a general explanation, not evidence identifying the exact change in these IMD bulletins. [ECMWF: data assimilation](https://www.ecmwf.int/en/research/data-assimilation).', '',
      'IMD describes separate district and block five-day forecast products. The supplied exports do not identify their precise upstream model configuration or establish identical spatial averaging. We must not assume that a district forecast equals an area-weighted average of the separately published block forecasts. [IMD: Agromet services](https://internal.imd.gov.in/press_release/20220824_pr_1790.pdf).', '',
      '### 3. The reference area changes inside our model', '',
      'Let c(v) be the learned seasonal rainfall climatology for village v; Cb and Cd are its block and district area-weighted reference climatologies. Let Sb and Sd be the official block and district inputs for the date.', '',
      '```text\nBlock factor fb = c(v) / Cb\nDistrict factor fd = c(v) / Cd\nBlock local B = Sb × fb\nDistrict local D = Sd × fd\nB / D = (Sb / Sd) × (Cd / Cb)  [when denominators are nonzero]\n```', '',
      'The same village numerator cancels in the ratio. Within a block and date, the two unrounded local fields are therefore proportional. Their spatial patterns are not independent evidence of agreement: both reuse the same learned field. Absolute gaps can still grow with the village factor. Coincidentally equal outputs can arise through cancellation.', '',
      'There is no fresh terrain change, random ensemble noise or day-specific local storm model in this implementation. Rainfall factors are fixed across these dates; most day-to-day variation comes from the parent inputs. Real precipitation can vary with atmospheric moisture, circulation and storm placement, which this static local transfer does not explicitly model.', '',
      '### 4. Exact algebraic separation', '',
      'We use a symmetric split so neither route is privileged as the reference. These are mathematical contributions, not causal estimates or percentages of accuracy:', '',
      '```text\nSource component = (Sb − Sd) × (fb + fd) / 2\nReference component = (Sb + Sd) × (fb − fd) / 2\nSource component + Reference component = B − D\n```', '',
      'Output rounding leaves a residual below 0.0001 mm. Signed contributions may oppose each other; absolute contributions do not add to the absolute final gap when cancellation occurs.', '',
      '| Date | Mean signed source component | Mean signed reference component | Mean absolute source component | Mean absolute reference component |', '|---|---:|---:|---:|---:|']
    for r in reports:
        s=r['summary'];lines.append('| '+r['valid_date']+' | '+' | '.join(f(s[k]) for k in ['mean_source_component_mm','mean_reference_component_mm','mean_absolute_source_component_mm','mean_absolute_reference_component_mm'])+' |')
    lines += ['', '## Every block on every shared date', '',
      'Source columns are official parent values. Local columns are equal-village means. The factor column is the mean block factor / mean district factor; its ratio reflects changing reference areas.', '',
      '| Date | Block | N | Block source | District source | Block local mean | District local mean | Mean signed gap | Mean absolute gap | Mean factors B / D |', '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in reports:
        for s in r['by_block']:
            rs=[x for x in r['rows'] if x['block']==s['block']]
            lines.append(f"| {r['valid_date']} | {s['block']} | {s['count']} | {f(rs[0]['block_source_mm'])} | {f(rs[0]['district_source_mm'])} | {f(s['block_mean_mm'])} | {f(s['district_mean_mm'])} | {f(s['mean_difference_mm'])} | {f(s['mean_absolute_difference_mm'])} | {sum(x['block_factor'] for x in rs)/len(rs):.4f} / {sum(x['district_factor'] for x in rs)/len(rs):.4f} |")
    lines += ['', '## Largest village disagreements', '', '| Date | Village | Block | Block local | District local | Gap | % vs district |', '|---|---|---|---:|---:|---:|---:|']
    for r in reports:
        for x in r['top_disagreements']:
            pct=f(x['percent_vs_district']) if x['percent_vs_district'] is not None else 'undefined'
            lines.append(f"| {r['valid_date']} | {x['name']} ({x['panchayat_id']}) | {x['block']} | {f(x['block_local_mm'])} | {f(x['district_local_mm'])} | {f(x['difference_mm'])} | {pct}% |")
    lines += ['', '## Practical implications', '',
      f"The routes fall on opposite sides of the application's ≥20 mm advisory trigger in {aggregate['different_20mm_trigger']:,} village-date pairs. This is an app-rule sensitivity check, not an official hazard category, measured agricultural impact or evidence that either advisory is correct.", '',
      'Do not silently average the routes, choose the larger number as truth, or treat their spread as a calibrated confidence interval. The same local model makes their errors correlated, and their different issue times confound a direct skill comparison. Retain both source labels and dates; use disagreement to identify cases for review.', '',
      'For a fair model evaluation, collect block and district forecasts from the same issue cycle for identical accumulation hours and lead times, retain their original files, and pair both with independent village/rain-gauge observations. Evaluate wet/dry cases, rainfall thresholds, bias, MAE/RMSE and event skill by lead time and geography using withheld periods. Compare against unchanged-parent forecasts as well as these adjusted paths. Only then assess whether selecting or blending improves performance.', '',
      '## Limits and reproducibility', '',
      'The terrain model was fitted to coarse NASA POWER seasonal proxies, with only five distinct historic profiles in Nashik. Local factors and footprint-mean assumptions are experimental; neither within-block accuracy nor prediction intervals are validated. A date match does not verify identical accumulation intervals. Source authenticity is not cryptographically attested. The comparison does not repair those limitations.', '',
      f"Model: `{first['block_source']['model_version']}`. Block run: `{first['block_source']['run_id']}`. District run: `{first['district_source']['run_id']}`.", '',
      f"The adjacent [{identity}.json]({identity}.json) contains the frozen district source bulletin, every paired village row, factor, component and summary. Block raw-source provenance remains in the named immutable run and imported dataset. Regenerate with `.venv\\Scripts\\python scripts/report_forecast_comparison.py`; this reads the current local district cache without a network request and creates a different snapshot if either run changes.", '',
      'The UI comparison view pins both runs while changing dates and blocks. Compare latest sources explicitly starts a new pairing. A missing overlap, mismatched model, unresolved village or unavailable variable is never replaced with a fabricated value.']
    text='\n'.join(lines)+'\n'
    out=folder/(identity+'.md')
    if out.exists() and out.read_text(encoding='utf-8') != text:
        raise ValueError('Existing report differs; preserve it and use a new report revision')
    out.write_text(text,encoding='utf-8')
    print(out)
    for r in reports: print(r['valid_date'],r['summary'])

if __name__=='__main__': generate()
