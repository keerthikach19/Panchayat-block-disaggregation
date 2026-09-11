import React, { useEffect, useState } from 'react';
import MapDashboard from './components/MapDashboard';
import ExplainabilityPanel from './components/ExplainabilityPanel';
import ValidationView from './components/ValidationView';
import './hybrid.css';

async function get(path, signal) {
  const res = await fetch(path, { signal });
  const body = await res.json();
  if (!res.ok) throw new Error(body.detail || 'Forecast unavailable');
  return body;
}
export default function App() {
  const [mode, setMode] = useState('block');
  const [runs, setRuns] = useState([]);
  const [run, setRun] = useState('');
  const [date, setDate] = useState('');
  const [block, setBlock] = useState('');
  const [blocks, setBlocks] = useState([]);
  const [forecast, setForecast] = useState(null);
  const [geo, setGeo] = useState(null);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [refresh, setRefresh] = useState(0);
  const key = [mode, 'Nashik', run, block, date, refresh].join('|');

  useEffect(() => {
    const controller = new AbortController();
    get('/api/blocks?district=Nashik', controller.signal).then(x => setBlocks(x.blocks)).catch(() => {});
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(''); setRuns([]); setRun(''); setDate('');
    setForecast(null); setGeo(null); setDetail(null); setSelected(null);
    get('/api/forecast/runs?district=Nashik&mode=' + mode, controller.signal)
      .then(x => { if (!controller.signal.aborted) { setRuns(x.runs); setRun(x.default_run_id); } })
      .catch(e => { if (e.name !== 'AbortError') { setError(e.message); setLoading(false); } });
    return () => controller.abort();
  }, [mode, refresh]);

  useEffect(() => {
    if (!run) return;
    const controller = new AbortController();
    let live = true;
    setLoading(true); setError(''); setForecast(null); setGeo(null); setSelected(null); setDetail(null);
    const query = new URLSearchParams({ mode, district: 'Nashik', run_id: run });
    if (date) query.set('valid_date', date);
    if (block) query.set('block', block);
    Promise.all([get('/api/forecast?' + query, controller.signal), get('/api/panchayats/geojson?' + query, controller.signal)])
      .then(([f, g]) => { if (live) { setForecast(f); setGeo(g); } })
      .catch(e => { if (live && e.name !== 'AbortError') setError(e.message); })
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; controller.abort(); };
  }, [key]);

  useEffect(() => {
    setDetail(null);
    if (!selected || !forecast) return;
    const controller = new AbortController();
    const query = new URLSearchParams({ mode: forecast.mode, district: 'Nashik', run_id: forecast.run_id, valid_date: forecast.valid_date });
    get('/api/panchayat/' + encodeURIComponent(selected) + '/explainability?' + query, controller.signal)
      .then(x => { if (!controller.signal.aborted) setDetail(x); })
      .catch(e => { if (e.name !== 'AbortError') setError(e.message); });
    return () => controller.abort();
  }, [selected, forecast]);

  const availableDates = runs.find(r => r.run_id === run)?.valid_dates || [];
  const chosenDay = date || forecast?.valid_date || '';
  return <main className="hybrid">
    <header className="hybrid-header"><div><span className="eyebrow">NASHIK · IMD FORECAST INPUTS</span><h1>Weather Downscaling Dashboard</h1></div><span className="method-chip">{forecast ? (forecast.model_version.startsWith('terrain-') ? 'Experimental terrain model' : 'Parent forecast baseline') : 'Loading model…'}</span></header>
    <section className="controls" aria-label="Forecast selection">
      <label>District<select value="Nashik" onChange={() => {}}><option>Nashik</option></select></label>
      <label>Forecast source<select value={mode} onChange={e => { setMode(e.target.value); setBlock(''); }}><option value="block">Official block forecasts</option><option value="district">Live district forecast</option></select></label>
      <label>Forecast day<select value={chosenDay} onChange={e => setDate(e.target.value)} disabled={!availableDates.length}>{!chosenDay && <option value="">Selecting date…</option>}{availableDates.map(d => <option key={d}>{d}</option>)}</select></label>
      <label>Block<select value={block} onChange={e => setBlock(e.target.value)}><option value="">All available blocks</option>{blocks.map(b => <option key={b.id} value={b.name}>{b.name}{forecast?.coverage.missing_blocks.includes(b.name) ? ' — unavailable' : ''}</option>)}</select></label>
      {mode === 'district' && <button onClick={() => setRefresh(x => x + 1)}>Fetch district bulletin</button>}
    </section>
    {error && <div role="alert" className="status warning"><strong>Forecast unavailable</strong><p>{error}</p><button onClick={() => setRefresh(x => x + 1)}>Retry</button></div>}
    {loading && <p role="status">Loading the selected forecast…</p>}
    {forecast && <>
      <section className={'status ' + (forecast.freshness === 'archived' ? 'warning' : '')}>
        <div><strong>{forecast.freshness === 'archived' ? 'Archived demonstration' : forecast.freshness === 'upcoming' ? 'Upcoming forecast' : 'Current forecast period'}</strong><p>Issued: {forecast.issue_date || 'Not provided'} · Forecast period: {forecast.valid_dates[0]}–{forecast.valid_dates.at(-1)} · Selected: {forecast.valid_date} (Asia/Kolkata)</p></div>
        <div><strong>{forecast.coverage.available_blocks}/{forecast.coverage.expected_blocks} blocks</strong><p>{forecast.data.length.toLocaleString()} linked villages · {forecast.coverage.excluded_features} excluded features</p></div>
      </section>
      <p className="source-note">{mode === 'block' ? 'IMD · Manually imported official block tables' : 'IMD · District-derived estimates'} · {forecast.cache_status}{forecast.downloaded_at && ' · Downloaded ' + forecast.downloaded_at}</p>
      {forecast.last_retrieval_error && <p className="warning">Retrieval failed; showing cached source: {forecast.last_retrieval_error}</p>}
      <div className="workspace"><MapDashboard key={key} geojsonLayer={geo} onSelectPanchayat={setSelected} selectedPanchayatId={selected} forecastMeta={forecast}/><ExplainabilityPanel key={key + selected} explainData={detail} loading={Boolean(selected && !detail)}/></div>
      <section className="notes"><p><strong>Geographic limitation:</strong> {forecast.geographic_limitation}</p><p>{forecast.model.status}</p>
      {forecast.model.config && <details><summary>Model assumptions</summary><p>{forecast.model.config.rainfall_reference_assumption}</p><p>{forecast.model.config.temperature_reference_assumption}</p></details>}
      {forecast.coverage.missing_blocks.length > 0 && <p>Missing blocks: {forecast.coverage.missing_blocks.join(', ')}. No replacement forecasts or advisories are generated.</p>}
      {forecast.import_warnings?.length > 0 && <details><summary>{forecast.import_warnings.length} source warnings</summary><ul>{forecast.import_warnings.map((w,i) => <li key={i}>{w.file}: {w.message}</li>)}</ul></details>}
      <details><summary>Source and processing record</summary><p>Dataset: {forecast.dataset_version}<br/>Run: {forecast.run_id}<br/>Method: {forecast.model_version}</p>{forecast.source_semantics?.length > 0 && <p>Import-stage notes below describe unchanged source normalization. Experimental adjustments use the separate model assumptions above.</p>}<ul>{forecast.source_semantics?.map(s => <li key={s}>{s}</li>)}</ul></details></section>
      <ValidationView modelVersion={forecast.model_version}/>
    </>}
  </main>;
}
