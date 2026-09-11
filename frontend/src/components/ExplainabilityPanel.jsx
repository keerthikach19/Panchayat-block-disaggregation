import React, { useState } from 'react';
export default function ExplainabilityPanel({ explainData: p, loading }) {
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState('');
  React.useEffect(() => { setPreview(null); setError(''); }, [p]);
  if (!p) return <aside className="detail-panel"><h2>{loading ? 'Loading source details…' : 'Explore a village'}</h2><p>Select a colored polygon to see its parent input, method and advisory preview.</p></aside>;
  const fields = [['temp_max_c', 'Maximum temperature', '°C'], ['temp_min_c', 'Minimum temperature', '°C'],
    ['relative_humidity_max_pct', 'Maximum humidity', '%'], ['relative_humidity_min_pct', 'Minimum humidity', '%'],
    ['cloud_cover_oktas', 'Cloud cover', 'oktas'], ['wind_speed_kmph', 'Wind speed', 'km/h'], ['wind_direction_deg', 'Wind direction', '°']];
  async function showPreview() {
    const res = await fetch('/api/disseminate/preview', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({panchayat_id:p.panchayat_id,mode:p.mode,run_id:p.run_id,valid_date:p.valid_date,channel:'WhatsApp'}) });
    const body = await res.json();
    if (!res.ok) throw new Error(body.detail || 'Preview unavailable');
    setPreview(body.rendered_preview);
  }
  return <aside className="detail-panel"><span className="eyebrow">VILLAGE SOURCE DETAILS</span><h2>{p.panchayat_name}</h2><p>{p.block_name} block · {p.panchayat_id}</p><p>Issue: {p.issue_date || 'Unknown'}<br/>Valid: {p.valid_date}</p>
    <div className="rain-pair"><div><span>Source {p.mode}</span><strong>{p.source_rainfall_mm} <small>mm</small></strong></div><div><span>Local estimate</span><strong>{Number(p.local_rainfall_mm).toFixed(2)} <small>mm</small></strong></div></div>
    <p>Rainfall adjustment: {Number(p.adjustment_mm).toFixed(2)} mm. {p.model.status}</p>
    {p.adjustment_details && <div className="terrain-details"><p>Copernicus elevation: {p.adjustment_details.village_elevation_m.toFixed(1)} m<br/>Rainfall factor: {p.adjustment_details.rainfall_factor.toFixed(3)}{p.temp_max_c != null && <><br/>Assumed parent elevation: {p.adjustment_details.block_reference_elevation_m.toFixed(1)} m<br/>Temperature adjustment: {p.adjustment_details.temperature_adjustment_c.toFixed(2)} °C</>}</p></div>}
    <table><caption>Source compared with local estimate</caption><thead><tr><th>Variable</th><td>Source</td><td>Local</td></tr></thead><tbody>{fields.map(([k,n,u]) => <tr key={k} title={p.variable_status[k]}><th>{n}<small style={{display:'block',fontSize:11,color:'#94a3b8'}}>{p.variable_status[k]}</small></th><td>{p.source[k] == null ? '—' : p.source[k] + ' ' + u}</td><td>{p[k] == null ? '—' : p[k] + ' ' + u}</td></tr>)}</tbody></table>
    <details><summary>Original source</summary><p className="wrap">{p.source.source_filename || p.source.source_url}</p>{p.source.sources?.map(s => <p className="wrap" key={s.filename}>{s.filename}<br/>SHA-256: {s.sha256}</p>)}<p>{p.model.status}</p></details>
    <section className="advisory"><h3>{p.advisory.historical ? 'Historical advisory preview' : 'Advisory preview'}</h3><p>{p.advisory.text}</p><p>Weather-triggered guidance; field conditions and crop stage require local review.</p><button onClick={() => showPreview().catch(e => setError(e.message))}>Preview dissemination</button>{error && <p role="alert">{error}</p>}{preview && <pre>{preview}</pre>}<small>Preview only. No messages are sent. No officer approval gate is claimed.</small></section>
  </aside>;
}
