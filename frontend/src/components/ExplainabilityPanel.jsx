import React, { useState } from 'react';
export default function ExplainabilityPanel({ explainData: p, loading }) {
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState('');
  React.useEffect(() => { setPreview(null); setError(''); }, [p]);
  if (!p) return <aside className="detail-panel"><h2>{loading ? 'Loading source details…' : 'Explore a village'}</h2><p>Select a colored polygon to see its parent input, method and advisory preview.</p></aside>;
  const fields = [['temp_max_c', 'Maximum temperature', '°C'], ['temp_min_c', 'Minimum temperature', '°C']];
  const sourceFields = [['relative_humidity_max_pct', 'Maximum humidity', '%'], ['relative_humidity_min_pct', 'Minimum humidity', '%'], ['wind_speed_kmph', 'Wind speed', 'km/h']];
  async function showPreview() {
    const res = await fetch('/api/disseminate/preview', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({panchayat_id:p.panchayat_id,mode:p.mode,run_id:p.run_id,valid_date:p.valid_date,channel:'WhatsApp'}) });
    const body = await res.json();
    if (!res.ok) throw new Error(body.detail || 'Preview unavailable');
    setPreview(body.rendered_preview);
  }
  return <aside className="detail-panel"><span className="eyebrow">VILLAGE SOURCE DETAILS</span><h2>{p.panchayat_name}</h2><p>{p.block_name} block · {p.panchayat_id}</p><p>Issue: {p.issue_date || 'Unknown'}<br/>Valid: {p.valid_date}</p>
    <div className="rain-pair"><div><span>Official {p.mode} forecast</span><strong>{p.source_rainfall_mm} <small>mm</small></strong></div><div><span>Village estimate</span><strong>{Number(p.local_rainfall_mm).toFixed(2)} <small>mm</small></strong></div></div>
    <p>{Math.abs(Number(p.adjustment_mm)) < 0.005 ? 'The village rainfall estimate is the same as the official forecast at the displayed precision.' : `The village estimate is ${Math.abs(Number(p.adjustment_mm)).toFixed(2)} mm ${Number(p.adjustment_mm) < 0 ? 'lower' : 'higher'} than the official forecast.`} This is an experimental estimate; its accuracy has not been measured against village observations.</p>
    {p.adjustment_details && <details className="terrain-details"><summary>How elevation and terrain change the estimate</summary><p>Village elevation (Copernicus): {p.adjustment_details.village_elevation_m.toFixed(1)} m<br/>Rainfall multiplier: {p.adjustment_details.rainfall_factor.toFixed(3)}{p.temp_max_c != null && <><br/>Assumed source-area elevation: {(p.adjustment_details.parent_reference_elevation_m ?? p.adjustment_details.block_reference_elevation_m).toFixed(1)} m<br/>Change applied to both temperatures: {p.adjustment_details.temperature_adjustment_c.toFixed(2)} °C</>}</p><p>These are terrain-based assumptions. They do not measure local storms or prove forecast accuracy.</p></details>}
    <table><caption>Temperature: official forecast and village estimate</caption><thead><tr><th>Variable</th><th>Official</th><th>Village</th></tr></thead><tbody>{fields.map(([k,n,u]) => <tr key={k} title={p.variable_status[k]}><th>{n}</th><td>{p.source[k] == null ? '—' : p.source[k] + ' ' + u}</td><td>{p[k] == null ? '—' : p[k] + ' ' + u}</td></tr>)}</tbody></table>
    <table><caption>Humidity and wind from the official forecast</caption><thead><tr><th>Variable</th><th>Forecast value</th></tr></thead><tbody>{sourceFields.map(([k,n,u])=><tr key={k}><th>{n}</th><td>{p.source[k] == null ? '—' : p.source[k]+' '+u}</td></tr>)}</tbody></table>
    <p>{p.mode==='district' ? 'Wind speed and humidity come from one district forecast, so every village receives the same values for this date.' : 'Wind speed and humidity come from the selected block forecast, so villages within that block share these values.'} The current model adjusts rainfall and temperature only.</p>
    <details><summary>Original source</summary><p className="wrap">{p.source.source_filename || p.source.source_url}</p>{p.source.sources?.map(s => <p className="wrap" key={s.filename}>{s.filename}<br/>SHA-256: {s.sha256}</p>)}<p>{p.model.status}</p></details>
    <p><a className="bulletin-link" target="_blank" rel="noreferrer" href={"/api/bulletin/"+encodeURIComponent(p.panchayat_id)+"?"+new URLSearchParams({mode:p.mode,run_id:p.run_id})}>Open printable five-day GKMS-style bulletin ↗</a></p>
    <section className="advisory"><h3>{p.advisory.historical ? 'Historical advisory preview' : 'Advisory preview'}</h3><p>{p.advisory.text}</p><p>Check field conditions and crop stage before acting on this guidance.</p><button onClick={() => showPreview().catch(e => setError(e.message))}>Preview message</button>{error && <p role="alert">{error}</p>}{preview && <pre>{preview}</pre>}<small>Preview only. No messages are sent.</small></section>
  </aside>;
}
