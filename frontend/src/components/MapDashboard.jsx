import React, { useState, useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

function MapController({ center, zoom }) {
  const map = useMap();
  useEffect(() => {
    if (center && zoom) {
      map.flyTo(center, zoom, { duration: 1.2 });
    }
  }, [center?.[0], center?.[1], zoom, map]);
  return null;
}

/**
 * Compute dynamic color thresholds from the actual data range using
 * quantile-based breaks so the map always shows a full gradient regardless
 * of whether block-mean rain is 4 mm or 40 mm.
 */
function computeDynamicThresholds(geojsonLayer) {
  if (!geojsonLayer?.features?.length) return null;

  const values = geojsonLayer.features
    .map(f => f.properties?.downscaled_rain_pred)
    .filter(v => v !== undefined && v !== null)
    .map(Number)
    .filter(v => !isNaN(v));

  if (values.length === 0) return null;

  const sorted = [...values].sort((a, b) => a - b);
  const pct = (p) => {
    const idx = Math.floor(p * (sorted.length - 1));
    return sorted[idx];
  };

  return {
    min: sorted[0],
    max: sorted[sorted.length - 1],
    p20: pct(0.20),
    p40: pct(0.40),
    p60: pct(0.60),
    p80: pct(0.80),
    mean: values.reduce((a, b) => a + b, 0) / values.length,
  };
}

// Five-stop color ramp: dry → wet
const COLOR_RAMP = ['#7dd3fc', '#38bdf8', '#0284c7', '#4f46e5', '#1e1b4b'];

export default function MapDashboard({
  district,
  onSelectPanchayat,
  selectedPanchayatId,
  geojsonLayer,
  loading,
  forecastMeta
}) {
  const [viewMode, setViewMode] = useState('downscaled'); // 'downscaled' | 'block' | 'uncertainty'

  const center = district === 'Nashik' ? [20.15, 74.0] : [18.65, 74.05];
  const zoom = district === 'Nashik' ? 9.2 : 9.0;
  const blockMean = Number(forecastMeta?.block_uniform_rain_mm ?? (district === 'Nashik' ? 22.5 : 18.5));
  const validDate = forecastMeta?.forecast_input?.selected_forecast_date;

  // Compute dynamic thresholds whenever geojsonLayer changes
  const thresholds = useMemo(() => computeDynamicThresholds(geojsonLayer), [geojsonLayer]);

  const getPanchayatColor = (feature) => {
    const props = feature?.properties || {};
    const rain = props.downscaled_rain_pred !== undefined ? Number(props.downscaled_rain_pred) : blockMean;
    const uncertainty = Number(props.uncertainty_std || 3.8);

    if (viewMode === 'block') {
      return '#0284c7'; // Uniform block-level color across all panchayats
    }

    if (viewMode === 'uncertainty') {
      if (uncertainty < 3.2) return '#10b981'; // Low uncertainty / High Confidence (Green)
      if (uncertainty < 4.2) return '#f59e0b'; // Moderate (Amber)
      return '#f43f5e'; // High Uncertainty / Low Confidence (Rose)
    }

    // Downscaled Mode: Dynamic quantile-based color scale
    if (thresholds) {
      if (rain <= thresholds.p20) return COLOR_RAMP[0];
      if (rain <= thresholds.p40) return COLOR_RAMP[1];
      if (rain <= thresholds.p60) return COLOR_RAMP[2];
      if (rain <= thresholds.p80) return COLOR_RAMP[3];
      return COLOR_RAMP[4];
    }

    // Fallback if thresholds not yet computed
    return COLOR_RAMP[2];
  };

  const styleFeature = (feature) => {
    const isSelected = feature.properties?.panchayat_id === selectedPanchayatId;
    return {
      fillColor: getPanchayatColor(feature),
      weight: isSelected ? 3.5 : 0.8,
      opacity: 1,
      color: isSelected ? '#38bdf8' : 'rgba(255,255,255,0.22)',
      fillOpacity: isSelected ? 0.95 : 0.78
    };
  };

  const onEachFeature = (feature, layer) => {
    const props = feature.properties || {};
    const rain = props.downscaled_rain_pred !== undefined ? Number(props.downscaled_rain_pred) : blockMean;
    const unc = Number(props.uncertainty_std || 3.8);
    const pName = props.panchayat_name || 'Gram Panchayat';
    const bName = props.block_name || district;

    let tooltipContent = '';
    if (viewMode === 'downscaled') {
      const diff = rain - blockMean;
      const diffSign = diff >= 0 ? '+' : '';
      const diffColor = diff >= 0 ? '#34d399' : '#f87171';
      tooltipContent = `
        <div style="min-width: 190px; font-family: 'Inter', sans-serif;">
          <div style="font-size: 10px; color: #94a3b8; text-transform: uppercase; font-weight: 700; letter-spacing: 0.5px;">Taluka: ${bName}</div>
          <div style="font-size: 15px; font-weight: 800; color: #ffffff; margin: 2px 0 6px 0;">${pName}</div>
          <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 3px;">
            <span style="color: #94a3b8;">Downscaled 24h Rain:</span>
            <strong style="color: #38bdf8;">${rain.toFixed(1)} mm</strong>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 3px;">
            <span style="color: #64748b;">Coarse Block Mean:</span>
            <span style="color: #cbd5e1;">${blockMean.toFixed(1)} mm</span>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 12px;">
            <span style="color: #64748b;">Microclimate Bias:</span>
            <span style="color: ${diffColor}; font-weight: 700;">${diffSign}${diff.toFixed(1)} mm</span>
          </div>
          <div style="font-size: 10px; color: #38bdf8; margin-top: 6px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 4px; font-style: italic;">
            Click polygon to view full explainability
          </div>
        </div>
      `;
    } else if (viewMode === 'block') {
      tooltipContent = `
        <div style="min-width: 190px; font-family: 'Inter', sans-serif;">
          <div style="font-size: 10px; color: #94a3b8; text-transform: uppercase; font-weight: 700; letter-spacing: 0.5px;">Taluka: ${bName}</div>
          <div style="font-size: 15px; font-weight: 800; color: #ffffff; margin: 2px 0 6px 0;">${pName}</div>
          <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 3px;">
            <span style="color: #94a3b8;">Uniform Block Mean:</span>
            <strong style="color: #38bdf8;">${blockMean.toFixed(1)} mm</strong>
          </div>
          <div style="font-size: 10px; color: #94a3b8; margin-top: 4px; font-style: italic;">
            📦 Single block-level value across entire taluka
          </div>
        </div>
      `;
    } else {
      const confLevel = props.confidence_level || (unc < 3.2 ? 'HIGH' : unc < 4.2 ? 'MODERATE' : 'ELEVATED');
      const uncColor = unc < 3.2 ? '#34d399' : unc < 4.2 ? '#fbbf24' : '#fb7185';
      const ciLow = Math.max(0, rain - unc * 1.28).toFixed(1);
      const ciHigh = (rain + unc * 1.28).toFixed(1);
      tooltipContent = `
        <div style="min-width: 200px; font-family: 'Inter', sans-serif;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 10px; color: #94a3b8; text-transform: uppercase; font-weight: 700; letter-spacing: 0.5px;">Taluka: ${bName}</span>
            <span style="font-size: 9px; font-weight: 700; color: ${uncColor}; background: ${uncColor}22; border: 1px solid ${uncColor}44; padding: 1px 5px; border-radius: 4px;">${confLevel}</span>
          </div>
          <div style="font-size: 15px; font-weight: 800; color: #ffffff; margin: 2px 0 6px 0;">${pName}</div>
          <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 3px;">
            <span style="color: #94a3b8;">Ensemble Spread (σ):</span>
            <strong style="color: ${uncColor};">±${unc.toFixed(1)} mm</strong>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 3px;">
            <span style="color: #64748b;">80% Confidence Band:</span>
            <span style="color: #f8fafc; font-weight: 600;">[${ciLow} – ${ciHigh} mm]</span>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 12px;">
            <span style="color: #64748b;">Expected Rain:</span>
            <span style="color: #38bdf8; font-weight: 700;">${rain.toFixed(1)} mm</span>
          </div>
        </div>
      `;
    }

    layer.bindTooltip(tooltipContent, {
      sticky: true,
      direction: 'top',
      offset: [0, -10],
      className: 'custom-leaflet-tooltip'
    });

    layer.on({
      mouseover: (e) => {
        const l = e.target;
        l.setStyle({
          weight: 2.8,
          color: '#ffffff',
          fillOpacity: 0.95
        });
        l.bringToFront();
      },
      mouseout: (e) => {
        const l = e.target;
        const sel = props.panchayat_id === selectedPanchayatId;
        l.setStyle({
          fillColor: getPanchayatColor(feature),
          weight: sel ? 3.5 : 0.8,
          color: sel ? '#38bdf8' : 'rgba(255,255,255,0.22)',
          fillOpacity: sel ? 0.95 : 0.78
        });
      },
      click: () => {
        if (props.panchayat_id) {
          onSelectPanchayat(props.panchayat_id);
        }
      }
    });
  };

  // Legend label helpers
  const legendMin = thresholds ? thresholds.min.toFixed(1) : '—';
  const legendMax = thresholds ? thresholds.max.toFixed(1) : '—';
  const legendMean = thresholds ? thresholds.mean.toFixed(1) : blockMean.toFixed(1);

  // Dry/wet zone labels by district
  const dryLabel = district === 'Pune' ? 'Rain-Shadow Dry' : 'Rain-Shadow Dry';
  const wetLabel = district === 'Pune' ? 'Ghats Crest' : 'Ghats Crest';

  return (
    <div className="map-viewport-wrapper">
      {/* Floating View Mode Switcher */}
      <div className="map-floating-controls">
        <div className="toggle-group glass-panel">
          <button
            className={`toggle-btn ${viewMode === 'downscaled' ? 'active' : ''}`}
            onClick={() => setViewMode('downscaled')}
          >
            ✨ Disaggregated (After)
          </button>
          <button
            className={`toggle-btn ${viewMode === 'block' ? 'active' : ''}`}
            onClick={() => setViewMode('block')}
          >
            📦 Block Mean (Before)
          </button>
          <button
            className={`toggle-btn ${viewMode === 'uncertainty' ? 'active' : ''}`}
            onClick={() => setViewMode('uncertainty')}
          >
            🛡️ Ensemble Confidence
          </button>
        </div>

        {validDate && (
          <div className="state-a-subtext glass-panel">
            Forecast Valid: {validDate}
          </div>
        )}
      </div>

      {/* Loading Overlay */}
      {loading && (
        <div style={{
          position: 'absolute',
          top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(7, 11, 19, 0.75)',
          backdropFilter: 'blur(4px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          color: '#38bdf8',
          fontSize: '14px',
          fontWeight: '600'
        }}>
          🔄 Rendering {district} Panchayat Polygons...
        </div>
      )}

      {/* Leaflet Map */}
      <MapContainer
        center={center}
        zoom={zoom}
        scrollWheelZoom={true}
        zoomControl={false}
      >
        <MapController center={center} zoom={zoom} />
        {/* Dark-styled OpenStreetMap Base Layer */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          className="dark-tiles"
        />

        {geojsonLayer && (
          <GeoJSON
            key={`${district}-${viewMode}-${selectedPanchayatId}-${thresholds?.min}`}
            data={geojsonLayer}
            style={styleFeature}
            onEachFeature={onEachFeature}
          />
        )}
      </MapContainer>

      {/* Dynamic Map Color Scale Legend */}
      <div className="map-legend glass-panel">
        <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-main)', marginBottom: '4px' }}>
          {viewMode === 'downscaled'
            ? `24-hr Downscaled Precipitation — ${district} (mm)`
            : viewMode === 'block'
            ? `IMD Uniform Block Average (${blockMean.toFixed(1)} mm)`
            : 'Ensemble Uncertainty (Standard Error)'}
        </div>
        {viewMode === 'downscaled' ? (
          <>
            <div className="legend-bar"></div>
            <div className="legend-labels">
              <span>&lt; {legendMin} mm ({dryLabel})</span>
              <span>{legendMean} mm (Block Mean)</span>
              <span>&gt; {legendMax} mm ({wetLabel})</span>
            </div>
          </>
        ) : viewMode === 'block' ? (
          <div style={{ fontSize: '12px', color: '#38bdf8', padding: '4px 0' }}>
            ■ Uniform {blockMean.toFixed(1)} mm Assigned across all {district} blocks (Erases microclimate variation)
          </div>
        ) : (
          <div style={{ display: 'flex', gap: '12px', fontSize: '12px', marginTop: '6px' }}>
            <span style={{ color: '#34d399' }}>■ High Confidence (σ &lt; 3.2mm)</span>
            <span style={{ color: '#fbbf24' }}>■ Moderate (σ 3.2-4.2mm)</span>
            <span style={{ color: '#fb7185' }}>■ Elevated (σ &gt; 4.2mm)</span>
          </div>
        )}
      </div>
    </div>
  );
}

