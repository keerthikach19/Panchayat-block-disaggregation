import React, { useEffect, useState } from 'react';
export default function ValidationView({ modelVersion }) {
  const [report,setReport]=useState(null);
  const [error,setError]=useState('');
  useEffect(()=>{
    const controller=new AbortController();
    setReport(null);setError('');
    fetch('/api/validation-metrics?model_version='+encodeURIComponent(modelVersion),{signal:controller.signal})
      .then(async res=>{const data=await res.json();if(!res.ok)throw new Error(data.detail);return data;})
      .then(setReport).catch(e=>{if(e.name!=='AbortError')setError(e.message);});
    return ()=>controller.abort();
  },[modelVersion]);
  const proxy=report?.proxy_report;
  return <section className="notes"><h2>Model evaluation</h2>
    {error && <p role="alert">{error}</p>}
    {!report && !error && <p role="status">Loading model evaluation…</p>}
    {!report ? null : proxy ? <>
      <p><strong>Experimental terrain model · {proxy.selected_candidate.replaceAll('_',' ')}</strong></p>
      <p>{proxy.evaluation_kind}. No independent village forecast accuracy or calibrated prediction interval is claimed.</p>
      <details><summary>View model comparison and limitations</summary>
        <p>{proxy.protocol}</p>
        <table><caption>Spatially held-out August proxy climatology · mm/day</caption><thead><tr><th>Candidate</th><td>RMSE</td><td>MAE</td></tr></thead><tbody>{Object.entries(proxy.candidate_scores).map(([name,s])=><tr key={name}><th>{name === 'unchanged_parent' ? 'Regional-mean baseline' : name.replaceAll('_',' ')}</th><td>{s.validation_rmse_mm_per_day.toFixed(2)}</td><td>{s.validation_mae_mm_per_day.toFixed(2)}</td></tr>)}</tbody></table>
        <p>Later-period proxy test RMSE: {proxy.test.selected_rmse_mm_per_day.toFixed(2)} mm/day; regional-mean baseline: {proxy.test.unchanged_regional_mean_rmse_mm_per_day.toFixed(2)} mm/day.</p>
        <p>{proxy.source_audit.station_labels} location labels resolve to {proxy.source_audit.independent_profile_groups} distinct gridded profiles, including only {proxy.source_audit.nashik_profile_groups} in Nashik.</p>
        <ul>{proxy.limitations.map(x=><li key={x}>{x}</li>)}</ul>
      </details>
    </> : <p>{modelVersion}: unchanged parent forecast baseline. Independent local forecast evaluation is unavailable.</p>}
  </section>;
}
