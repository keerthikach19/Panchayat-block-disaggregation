import React from 'react';

const pct = value => value == null ? '—' : `${(100 * value).toFixed(1)}%`;
const number = value => value == null ? '—' : value.toFixed(2);
const modelName = value => ({raw_gfs: 'Uncorrected GFS', scaled_gfs: 'Scaled GFS', weather_tweedie: 'Weather-based amount model', rain_only_logistic: 'Forecast-rain classifier', weather_classifier: 'Weather-based event model'}[value] ?? value);

export default function NwpExperiment({report}) {
  const rows = report.by_lead;
  const passed = rows.filter(row => row.joint_50_50_met).length;
  return <section className="notes">
    <h3>Weather forecast model: independent 2026 test</h3>
    <p className="warning"><strong>50% detection and 50% precision: {passed} of {rows.length} leads reached both.</strong> These are measured point estimates on sampled Nashik grid-days, using provisional IMD observations. They do not establish village forecast accuracy.</p>
    <p>This model uses archived NOAA GFS forecasts of rainfall, humidity and atmospheric moisture, plus nearby forecast rainfall, location and season. It estimates rainfall amount and separately decides whether to alert for at least 20 mm.</p>
    <p><strong>Detection (recall)</strong> answers “Of the actual ≥20 mm cases, how many did we catch?” <strong>Precision</strong> answers “Of our alerts, how many were correct?” A 50% detection score alone can still come with many false alarms.</p>
    <div className="comparison-table"><table>
      <caption>≥20 mm alerts · same cases for uncorrected GFS and the selected model</caption>
      <thead><tr><th>Lead</th><th>GFS detection → selected</th><th>GFS precision → selected</th><th>Caught / actual cases</th><th>False / all alerts</th><th>CSI</th><th>Both ≥50%?</th></tr></thead>
      <tbody>{rows.map(row => <tr key={row.lead_days}>
        <th>Lead {row.lead_days}</th><td>{pct(row.raw_event.recall)} → {pct(row.event.recall)}</td>
        <td>{pct(row.raw_event.precision)} → {pct(row.event.precision)}</td>
        <td>{row.event.hits} / {row.event.observed_events}</td><td>{row.event.false_alarms} / {row.event.alerts} ({pct(row.event.false_alarm_ratio)})</td>
        <td>{number(row.event.csi)}</td><td>{row.joint_50_50_met ? 'Yes' : 'No'}</td>
      </tr>)}</tbody>
    </table></div>
    <p>One case means one 0.25° grid cell on one target date; nearby cases can belong to the same storm. CSI counts hits against hits + misses + false alarms; higher is better. The observed event definition stays at 20 mm.</p>
    <div className="comparison-table"><table>
      <caption>Rainfall amounts · uncorrected GFS → selected estimate · mm</caption>
      <thead><tr><th>Lead</th><th>MAE</th><th>RMSE</th><th>Bias</th><th>Amount ≥20 mm detection</th><th>Grid-day cases</th></tr></thead>
      <tbody>{rows.map(row => <tr key={row.lead_days}>
        <th>Lead {row.lead_days}</th><td>{number(row.raw_amount.mae_mm)} → {number(row.amount.mae_mm)}</td>
        <td>{number(row.raw_amount.rmse_mm)} → {number(row.amount.rmse_mm)}</td><td>{number(row.raw_amount.bias_mm)} → {number(row.amount.bias_mm)}</td>
        <td>{pct(row.amount.event_at_20mm.recall)}</td><td>{row.n}</td>
      </tr>)}</tbody>
    </table></div>
    <p>MAE is the average size of the rainfall error. RMSE penalizes larger errors more. Negative bias means underprediction. Alert detection is separate from accuracy of the rainfall amount.</p>
    <details><summary>How this was trained, selected and tested</summary>
      <p>Models were fitted on 2021–2023, probabilities calibrated on 2024, and candidates and thresholds selected on 2025. Nashik and its 0.25° buffer were excluded throughout. All choices were frozen before the 2026 Nashik audit.</p>
      <p>Alert selection aimed for both ≥50% detection and ≥50% precision, with a false-positive rate of at most 25%. Among qualifying choices it maximized CSI; if none qualified, it used the highest CSI and recorded the failed target. Rainfall amounts were selected separately using RMSE with MAE and bias constraints.</p>
      <p>These leads use 00:00 UTC GFS initializations. Lead 1 covers hours 27–51 after initialization; each later lead shifts that 24-hour window by one day. Every window ends at 03:00 UTC, matching the IMD observation period. A 12-hour publication buffer is assumed, not verified from historical delivery logs.</p>
      <ul>{rows.map(row => {
        const choice = report.selection.by_lead.find(r => r.lead_days === row.lead_days);
        return <li key={row.lead_days}>Lead {row.lead_days}: {modelName(row.selected_event)}; amount: {modelName(row.selected_amount)}. Joint validation target {choice.event_joint_target_met ? 'met' : 'not met'}. Test: {row.date_start} to {row.date_end}, {row.initializations} initialization dates. Approximate 95% intervals: detection {row.event_intervals_95.recall.map(pct).join('–')}; precision {row.event_intervals_95.precision.map(pct).join('–')}.</li>;
      })}</ul>
      <ul>{report.limitations.map(text => <li key={text}>{text}</li>)}</ul>
      <p className="wrap">Experiment: {report.experiment_id}<br/>Evaluation: {report.evaluation_id}</p>
      <p>Sources: <a href="https://dynamical.org/catalog/noaa-gfs-forecast/" target="_blank" rel="noreferrer">NOAA GFS processed by dynamical.org (CC BY 4.0)</a>; <a href="https://imdpune.gov.in/cmpg/Realtimedata/Rainfall/Rain_Download.html" target="_blank" rel="noreferrer">IMD provisional daily rainfall</a>.</p>
    </details>
    <p><strong>Research model:</strong> the map continues to show the official parent forecast with experimental local terrain adjustments. This GFS experiment has not replaced it.</p>
  </section>;
}
