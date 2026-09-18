import React from 'react';

const pct = value => value == null ? '—' : `${(100 * value).toFixed(1)}%`;
const mm = value => `${value.toFixed(2)} mm`;

export default function RainfallExperiment({report}) {
  const evaluations = Object.entries(report.evaluations).sort(([a], [b]) => a.localeCompare(b));
  const fresh = report.evaluations.fresh_2025?.by_lead;
  const range = values => `${pct(Math.min(...values))}–${pct(Math.max(...values))}`;
  return <section className="notes">
    <h3>Revised rainfall model: amounts and ≥20 mm alerts</h3>
    {fresh && <p className="warning"><strong>Fresh 2025 results:</strong> alerts detected {range(fresh.map(row => row.event.recall))} of ≥20 mm cases. {range(fresh.map(row => row.event.false_alarm_ratio))} of alerts were false alarms. Detection improved, but rainfall MAE worsened and event skill remains limited.</p>}
    {report.selection.by_lead.some(row => !row.event_selection.constraints_met) && <p>The combined validation targets were not met for every lead. The predeclared fallback selected the threshold with the best CSI. These models are not validated for operational warnings.</p>}
    <p>The revised model estimates rainfall amount and separately estimates the chance of at least 20 mm. An alert can be raised even when the amount estimate is below 20 mm. Alert detection is not rainfall-amount accuracy.</p>
    <p>Trained on 2010–2018, probabilities calibrated on 2019, and models and alert thresholds selected on 2020–2021. Nashik and its buffer are excluded from all three stages. Inputs include past rainfall, neighboring rainfall patterns, location and season.</p>
    <p>Selection balances detected events, false alarms and missed events. Rainfall-amount selection considers RMSE, bias and MAE. All model choices are frozen before evaluation.</p>
    {evaluations.map(([key, evaluation]) => <section key={key}>
      <h3>{key === 'fresh_2025' ? 'Fresh evaluation: Nashik, June–October 2025' : 'Before / after comparison: Nashik, June–October 2022–2024'}</h3>
      <p>{key === 'fresh_2025' ? 'This year was not used to fit, calibrate or select the revised model.' : 'These years were examined during earlier model development. This comparison is not a fresh holdout.'} Each case is one grid cell on one day.</p>
      <div className="comparison-table"><table>
        <caption>≥20 mm events: detection and false alarms</caption>
        <thead><tr><th>Lead</th><th>Old detection</th><th>New alert detection</th><th>Missed / observed</th><th>False / all alerts</th><th>Alert precision</th><th>CSI</th></tr></thead>
        <tbody>{evaluation.by_lead.map(row => <tr key={row.lead_days}>
          <th>Day {row.lead_days}</th><td>{pct(row.original.event_at_20mm.recall)}</td><td>{pct(row.event.recall)}</td>
          <td>{row.event.misses} / {row.event.observed_events}</td><td>{row.event.false_alarms} / {row.event.alerts}</td>
          <td>{pct(row.event.precision)}</td><td>{row.event.csi?.toFixed(3) ?? '—'}</td>
        </tr>)}</tbody>
      </table></div>
      <p>Detection: share of actual ≥20 mm cases alerted. Precision: share of alerts that occurred. CSI: hits divided by hits + misses + false alarms; 1 is best.</p>
      <div className="comparison-table"><table>
        <caption>Rainfall amounts: lower error is better; bias closer to zero is better</caption>
        <thead><tr><th>Lead</th><th>Old → new MAE</th><th>Old → new RMSE</th><th>Old → new bias</th><th>New amount ≥20 mm detection</th></tr></thead>
        <tbody>{evaluation.by_lead.map(row => <tr key={row.lead_days}>
          <th>Day {row.lead_days}</th><td>{mm(row.original.mae_mm)} → {mm(row.revised.mae_mm)}</td>
          <td>{mm(row.original.rmse_mm)} → {mm(row.revised.rmse_mm)}</td><td>{mm(row.original.bias_mm)} → {mm(row.revised.bias_mm)}</td>
          <td>{pct(row.revised.event_at_20mm.recall)}</td>
        </tr>)}</tbody>
      </table></div>
    </section>)}
    <details><summary>Frozen selection and research limits</summary>
      <p>Alert thresholds are selected to maximize CSI, aiming for at least 50% detection, at least 20% precision and at most 25% false positives among non-events on validation data. These are development targets, not guarantees on new data.</p>
      <ul>{report.selection.by_lead.map(row => <li key={row.lead_days}>Day {row.lead_days}: alert when probability ≥{pct(row.event_selection.threshold)}; validation alert constraints {row.event_selection.constraints_met ? 'met' : 'not met'}; amount model: {row.selected_amount}; amount constraints {row.amount_constraints_met ? 'met' : 'not met'}.</li>)}</ul>
      <ul>{report.limitations.map(text => <li key={text}>{text}</li>)}</ul>
      <p className="wrap">Experiment: {report.experiment_id}</p>
    </details>
    <p><strong>Research evaluation:</strong> these results do not replace the village forecasts on the map or establish village-level accuracy.</p>
  </section>;
}
