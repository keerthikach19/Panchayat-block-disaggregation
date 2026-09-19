import React, {useEffect, useState} from 'react';
import NwpExperiment from './NwpExperiment';

export default function ModelEvidence() {
  const [report, setReport] = useState(null), [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/model-evidence', {signal: controller.signal})
      .then(async response => {
        if (!response.ok) throw Error('Model report unavailable');
        return response.json();
      })
      .then(setReport)
      .catch(error => { if (error.name !== 'AbortError') setError(error.message); });
    return () => controller.abort();
  }, []);

  return <section className="comparison">
    <h2>Models and evaluation</h2>
    <section className="notes">
      <h3>How village forecasts are calculated</h3>
      <table><thead><tr><th>Variable</th><th>Method</th></tr></thead><tbody>
        <tr><th>Rainfall</th><td>Official forecast adjusted using local terrain and seasonal rainfall patterns.</td></tr>
        <tr><th>Maximum / minimum temperature</th><td>Official forecast adjusted using elevation and an assumed −6.5°C/km temperature change.</td></tr>
        <tr><th>Humidity and wind speed</th><td>Values from the official block or district forecast.</td></tr>
      </tbody></table>
      <p>Village estimates are experimental. Their accuracy has not been measured against independent village observations.</p>
    </section>
    {error && <p role="alert">{error}</p>}
    {!report && !error && <p role="status">Loading evaluation…</p>}
    {report?.nwp_benchmark && <NwpExperiment report={report.nwp_benchmark}/>}
    {report && !report.nwp_benchmark && <p role="status">Rainfall model evaluation is unavailable.</p>}
  </section>;
}
