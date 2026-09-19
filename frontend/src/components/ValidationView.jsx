import React, { useEffect, useState } from 'react';

export default function ValidationView({ modelVersion }) {
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    setReport(null); setError('');
    fetch('/api/validation-metrics?model_version=' + encodeURIComponent(modelVersion), {signal: controller.signal})
      .then(async response => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail);
        return data;
      })
      .then(setReport)
      .catch(error => { if (error.name !== 'AbortError') setError(error.message); });
    return () => controller.abort();
  }, [modelVersion]);

  const proxy = report?.proxy_report;
  return <section className="notes"><h2>Village model evaluation</h2>
    {error && <p role="alert">{error}</p>}
    {!report && !error && <p role="status">Loading model evaluation…</p>}
    {report && (proxy ? <>
      <p><strong>Terrain model · {proxy.selected_candidate.replaceAll('_', ' ')}</strong></p>
      <p>This model was evaluated on seasonal gridded rainfall patterns. Daily village forecast accuracy has not been independently measured.</p>
      <details><summary>Seasonal-pattern evaluation</summary>
        <table><caption>Held-out seasonal rainfall patterns · mm/day</caption>
          <thead><tr><th>MAE</th><th>RMSE</th></tr></thead>
          <tbody><tr><td>{proxy.test.selected_mae_mm_per_day.toFixed(2)}</td><td>{proxy.test.selected_rmse_mm_per_day.toFixed(2)}</td></tr></tbody>
        </table>
        <p>MAE is the average absolute error; RMSE gives larger errors more weight. These scores measure seasonal-pattern reconstruction, not daily weather forecasts.</p>
        <p>Evaluation used separate location-profile groups and a September–October period. The data contain {proxy.source_audit.independent_profile_groups} distinct gridded profiles, including {proxy.source_audit.nashik_profile_groups} in Nashik; they are not independent village gauges.</p>
      </details>
    </> : <p>Villages use the official parent forecast without a local adjustment. Independent village forecast accuracy is unavailable.</p>)}
  </section>;
}
