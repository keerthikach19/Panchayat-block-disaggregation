import React from 'react';

const pct = value => value == null ? '—' : `${(100 * value).toFixed(1)}%`;
const number = value => value == null ? '—' : value.toFixed(2);

export default function NwpExperiment({report}) {
  const rows = report.by_lead;
  const passed = rows.filter(row => row.joint_50_50_met).length;
  return <section className="notes">
    <h3>Rainfall model evaluation</h3>
    <p>The rainfall research model uses GFS rainfall, humidity and atmospheric moisture forecasts, nearby forecast rainfall, location and season. It estimates rainfall amounts and the chance of at least 20 mm.</p>
    <p><strong>Evaluation:</strong> Nashik, June–September 2026, using provisional IMD observations on a 0.25° grid. These scores describe the research model; the village map uses the terrain method described above.</p>

    <div className="comparison-table"><table>
      <caption>Rainfall amounts · errors in mm</caption>
      <thead><tr><th>Lead</th><th>MAE</th><th>RMSE</th><th>Bias</th><th>Amount ≥20 mm detection</th><th>Grid-day cases</th></tr></thead>
      <tbody>{rows.map(row => <tr key={row.lead_days}>
        <th>Lead {row.lead_days}</th><td>{number(row.amount.mae_mm)}</td>
        <td>{number(row.amount.rmse_mm)}</td><td>{number(row.amount.bias_mm)}</td>
        <td>{pct(row.amount.event_at_20mm.recall)}</td><td>{row.n}</td>
      </tr>)}</tbody>
    </table></div>
    <p><strong>MAE:</strong> average absolute error. <strong>RMSE:</strong> error measure that gives larger mistakes more weight. Lower is better for both. <strong>Bias:</strong> negative values mean underprediction.</p>
    <p>Amount detection is the share of actual ≥20 mm cases where the predicted rainfall amount also reached 20 mm.</p>

    <div className="comparison-table"><table>
      <caption>≥20 mm event alerts</caption>
      <thead><tr><th>Lead</th><th>Detection (recall)</th><th>Precision</th><th>Caught / actual cases</th><th>False alerts</th><th>CSI</th></tr></thead>
      <tbody>{rows.map(row => <tr key={row.lead_days}>
        <th>Lead {row.lead_days}</th><td>{pct(row.event.recall)}</td><td>{pct(row.event.precision)}</td>
        <td>{row.event.hits} / {row.event.observed_events}</td><td>{pct(row.event.false_alarm_ratio)}</td>
        <td>{row.event.csi == null ? '—' : row.event.csi.toFixed(3)}</td>
      </tr>)}</tbody>
    </table></div>
    <p><strong>Detection:</strong> share of actual events caught. <strong>Precision:</strong> share of alerts that were correct. <strong>False alerts:</strong> share of alerts that did not occur. <strong>CSI:</strong> hits divided by hits + misses + false alerts; higher is better.</p>
    <p>Alerts are based on event probability and are evaluated separately from rainfall amounts. {passed === 0 ? 'No lead reached both 50% detection and 50% precision.' : `${passed} of ${rows.length} leads reached both 50% detection and 50% precision.`}</p>

    <details><summary>Training, test coverage and uncertainty</summary>
      <p>Fitted on 2021–2023, probability-calibrated on 2024, and selected on 2025. Nashik and its 0.25° buffer were excluded from all three stages. Model choices and alert thresholds were fixed before the 2026 evaluation.</p>
      <p>The test uses 22 Nashik grid cells and 34 sampled forecast initializations per lead. Nearby grid-days can belong to the same storm. It covers part of one season, with provisional observations; it does not establish village forecast accuracy.</p>
      <p>Each lead covers 24 hours ending at 03:00 UTC. Lead 1 spans hours 27–51 after the 00:00 UTC forecast initialization, and each later lead shifts by one day. A 12-hour publication buffer is assumed; actual historical delivery times are unverified.</p>
      <div className="comparison-table"><table>
        <caption>Approximate 95% uncertainty intervals</caption>
        <thead><tr><th>Lead</th><th>Detection</th><th>Precision</th></tr></thead>
        <tbody>{rows.map(row => <tr key={row.lead_days}>
          <th>Lead {row.lead_days}</th><td>{row.event_intervals_95.recall.map(pct).join('–')}</td>
          <td>{row.event_intervals_95.precision.map(pct).join('–')}</td>
        </tr>)}</tbody>
      </table></div>
      <p>Intervals use 500 bootstrap samples of pairs of adjacent initialization dates, keeping each date’s grid cells together.</p>
      <p>Sources: <a href="https://dynamical.org/catalog/noaa-gfs-forecast/" target="_blank" rel="noreferrer">NOAA GFS processed by dynamical.org (CC BY 4.0)</a>; <a href="https://imdpune.gov.in/cmpg/Realtimedata/Rainfall/Rain_Download.html" target="_blank" rel="noreferrer">IMD provisional daily rainfall</a>.</p>
    </details>
  </section>;
}
