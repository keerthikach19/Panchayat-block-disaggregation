import React, { useState, useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, GeoJSON, ZoomControl, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

const WEATHER = {rainfall_mm:['Rainfall','mm'],temp_max_c:['Maximum temperature','°C'],temp_min_c:['Minimum temperature','°C'],relative_humidity_max_pct:['Maximum humidity','%'],relative_humidity_min_pct:['Minimum humidity','%'],wind_speed_kmph:['Wind speed','km/h'],wind_direction_deg:['Wind direction','°'],cloud_cover_oktas:['Cloud cover','oktas']};
const COLORS = ['#7dd3fc', '#38bdf8', '#0284c7', '#4f46e5', '#1e1b4b'];
function FitCoverage({ data }) {
  const map = useMap();
  useEffect(() => {
    const bounds = L.geoJSON(data).getBounds();
    if (bounds.isValid()) map.fitBounds(bounds, {padding:[30,80],maxZoom:11,animate:false});
  }, [map,data]);
  return null;
}
export default function MapDashboard({ geojsonLayer, onSelectPanchayat, selectedPanchayatId, forecastMeta }) {
  const [view, setView] = useState('local');
  const [variable,setVariable] = useState('rainfall_mm');
  const [label,unit] = WEATHER[variable];
  const [mapLabels, setMapLabels] = useState(false);
  const thresholds = useMemo(() => {
    const values = (geojsonLayer?.features || []).flatMap(f => [f.properties['source_'+variable], f.properties['local_'+variable]]).filter(Number.isFinite).sort((a,b)=>a-b);
    return values.length ? [0.2,0.4,0.6,0.8].map(q=>values[Math.floor(q*(values.length-1))]) : [5,20,50,100];
  },[geojsonLayer,variable]);
  const field = view + '_' + variable;
  function color(value) {
    if (!Number.isFinite(value)) return '#64748b';
    const index = thresholds.findIndex(t=>value<=t);
    return COLORS[index<0?4:index];
  }
  function style(f) {
    const selected=f.properties.panchayat_id===selectedPanchayatId;
    return {fillColor:color(f.properties[field]),weight:selected?3.5:.8,color:selected?'#38bdf8':'rgba(255,255,255,0.22)',fillOpacity:selected?.95:.78,dashArray:f.properties.available?null:'3 3'};
  }
  function onFeature(feature,layer) {
    const p=feature.properties;
    const card=document.createElement('div');
    card.style.cssText="min-width:200px;font-family:system-ui;line-height:1.6;color:#e2e8f0";
    const heading=document.createElement('strong');
    heading.style.cssText="font-size:16px;color:white";
    heading.textContent=p.panchayat_name;
    card.append(heading);
    for(const text of [
      'Block: '+(p.block_name || 'Unresolved'),
      Number.isFinite(p['source_'+variable])?'Source input: '+p['source_'+variable]+' '+unit:(variable==='cloud_cover_oktas' && p.source_cloud_description ? 'Source cloud: '+p.source_cloud_description : 'Source value unavailable'),
      Number.isFinite(p[field])?'Shown '+label+': '+p[field]+' '+unit:'No numeric estimate available',
      Number.isFinite(p['local_'+variable]) && Number.isFinite(p['source_'+variable])?'Adjustment: '+(p['local_'+variable]-p['source_'+variable]).toFixed(2)+' '+unit:'',
      p.available?'Click to view source and model details':''
    ]) {const line=document.createElement('div');line.textContent=text;card.append(line);}
    layer.bindTooltip(card,{sticky:true,direction:'top',offset:[0,-10],className:'custom-leaflet-tooltip'});
    layer.on({mouseover:e=>{e.target.setStyle({weight:2.8,color:'#fff',fillOpacity:.95});e.target.bringToFront();},
      mouseout:e=>e.target.setStyle(style(feature)),
      click:()=>{if(p.available)onSelectPanchayat(p.panchayat_id);}});
  }
  return <div className="map-viewport-wrapper">
    <div className="map-floating-controls">
      <label className="weather-selector glass-panel">Weather variable <select value={variable} onChange={e=>setVariable(e.target.value)}>{Object.entries(WEATHER).map(([k,[n,u]])=><option value={k} key={k}>{n} ({u})</option>)}</select></label>
      <div className="toggle-group glass-panel">
        <button className={'toggle-btn '+(view==='local'?'active':'')} aria-pressed={view==='local'} onClick={()=>setView('local')}>✨ Local estimates (After)</button>
        <button className={'toggle-btn '+(view==='source'?'active':'')} aria-pressed={view==='source'} onClick={()=>setView('source')}>📦 Source input (Before)</button>
      </div>
      <div className="state-a-subtext glass-panel">Forecast valid: {forecastMeta?.valid_date} · {forecastMeta?.mode==='block'?'Official block source':'District source'}</div>
      <label className="state-a-subtext glass-panel"><input type="checkbox" checked={mapLabels} onChange={e=>setMapLabels(e.target.checked)}/> Street map labels (online)</label>
    </div>
    <MapContainer center={[20.15,74.0]} zoom={9.2} scrollWheelZoom zoomControl={false} zoomAnimation={false} fadeAnimation={false} markerZoomAnimation={false}>
      {geojsonLayer && <FitCoverage data={geojsonLayer}/>}
      <ZoomControl position="topright"/>
      {mapLabels && <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" className="dark-tiles"/>}
      {geojsonLayer && <GeoJSON key={variable+'|'+view+'|'+selectedPanchayatId} data={geojsonLayer} style={style} onEachFeature={onFeature}/>}
    </MapContainer>
    <div className="map-legend glass-panel">
      <strong>{view==='source'?'Source':'Local'} {label.toLowerCase()} · {unit}</strong>
      <div className="legend-bar"/>
      <div className="legend-labels"><span>Lower value</span><span>Higher value</span></div>
      <p className="scale-values">Shared breaks: {thresholds.map(v=>v.toFixed(1)).join(' / ')} {unit}</p>
      <p className="scale-values">Gray: unavailable · Village polygons</p>
      <p className="scale-values">{variable.startsWith('temp_')?'Temperature: experimental elevation adjustment.':variable!=='rainfall_mm'?'Inherited from parent; no validated local adjustment.':'Rainfall: experimental terrain adjustment.'}</p>
      <p className="scale-values">Before view repeats each parent's forecast over its villages.</p>
    </div>
  </div>;
}
