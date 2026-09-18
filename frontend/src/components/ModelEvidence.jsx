import React, {useEffect,useState} from 'react';
import RainfallExperiment from './RainfallExperiment';
import NwpExperiment from './NwpExperiment';
export default function ModelEvidence(){
  const [report,setReport]=useState(null),[error,setError]=useState('');
  useEffect(()=>{const c=new AbortController();fetch('/api/model-evidence',{signal:c.signal}).then(async r=>{if(!r.ok)throw Error('Model report unavailable');return r.json();}).then(setReport).catch(e=>{if(e.name!=='AbortError')setError(e.message);});return()=>c.abort();},[]);
  return <section className="comparison"><h2>Model training and release decision</h2>
    <p>The release uses official parent weather forecasts, terrain-adjusted rainfall and temperature, and inherited humidity and wind speed. Training results below describe a separate historical benchmark.</p>
    <section className="notes"><h3>Final serving method</h3><table><thead><tr><th>Weather variable</th><th>Method</th><th>Evidence boundary</th></tr></thead><tbody>
      <tr><th>Rainfall</th><td>Ridge climate pattern with area-normalized terrain factors</td><td>Proxy climatology evaluated; local forecast skill unverified</td></tr>
      <tr><th>Maximum / minimum temperature</th><td>Copernicus elevation and −6.5°C/km lapse rate</td><td>Physical assumption; not a locally calibrated temperature model</td></tr>
      <tr><th>Humidity and wind speed</th><td>Official parent value inherited</td><td>No fabricated fine-scale variation</td></tr>
    </tbody></table></section>
    {error && <p role="alert">{error}</p>}{!report && !error && <p role="status">Loading training evidence…</p>}
    {report?.nwp_benchmark && <NwpExperiment report={report.nwp_benchmark}/>}
    {report?.revised_benchmark && <details><summary>Earlier model: rainfall history only (2025 evaluation)</summary><RainfallExperiment report={report.revised_benchmark}/></details>}
    {report && <><section className="notes"><h3>Original benchmark: selected by average error</h3><p>IMD daily 0.25° rainfall analyses, 2010–2024: {report.state_cells} state grid cells, {report.nashik_cells} Nashik test cells. Train: 2010–2018; validation: 2019–2021; Nashik test: 2022–2024. Nashik and its 0.25° buffer are excluded from training and validation. June–October only.</p><p>Four candidates per lead: persistence, monthly climatology, LightGBM absolute loss and Tweedie loss. Selection used validation MAE before examining the test set.</p>
    <div className="comparison-table"><table><caption>Held-out Nashik grid-day scores · mm · retrospective benchmark</caption><thead><tr><th>Lead</th><th>Selected MAE</th><th>Persistence MAE</th><th>RMSE</th><th>Bias</th><th>≥20 mm events missed</th></tr></thead><tbody>{report.by_lead.map(l=>{const s=l.nashik_test[l.selected];return <tr key={l.lead_days}><th>Day {l.lead_days}</th><td>{s.mae_mm.toFixed(2)}</td><td>{l.nashik_test.persistence.mae_mm.toFixed(2)}</td><td>{s.rmse_mm.toFixed(2)}</td><td>{s.bias_mm.toFixed(2)}</td><td>{s.heavy_20mm_misses} / {s.heavy_20mm_n}</td></tr>;})}</tbody></table></div></section>
    <section className="notes"><h3>Map forecasts remain experimental</h3><p>The original model's lower average error hid severe underprediction of rainfall. The latest research experiment uses archived GFS forecasts; the earlier models used rainfall history. None calibrates the issued IMD block forecasts shown on the map. Independent, time-aligned local observations are needed to establish village forecast accuracy.</p><details><summary>Original benchmark data and limitations</summary><p className="wrap">Experiment: {report.experiment_id}<br/>Dataset: {report.dataset_version}</p><ul>{report.limitations.map(s=><li key={s}>{s}</li>)}</ul></details></section></>}
  </section>;
}
