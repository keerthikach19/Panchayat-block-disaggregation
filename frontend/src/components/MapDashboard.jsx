import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

function MapController({ center, zoom, geojsonLayer }) {
  const map = useMap();
  useEffect(() => {
    if (center && zoom) {
      map.flyTo(center, zoom, { duration: 1.2 });
    }
  }, [center?.[0], center?.[1], zoom, map]);
  return null;
}

export default function MapDashboard({
  district,
  onSelectPanchayat,
  selectedPanchayatId,
  geojsonLayer,
  loading
}) {
  const [viewMode, setViewMode] = useState('downscaled'); // 'downscaled' | 'block' | 'uncertainty'

  const center = district === 'Nashik' ? [20.15, 74.0] : [18.65, 74.05];
  const zoom = district === 'Nashik' ? 9.2 : 9.0;
  const blockMean = district === 'Nashik' ? 22.5 : 18.5;

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

    // Downscaled Mode: Orographic color scale tailored to district variance
    if (district === 'Pune') {
      if (rain < 14.5) return '#7dd3fc';      // Rain-shadow dry east (Daund/Indapur/Baramati)
      if (rain < 17.5) return '#38bdf8';
      if (rain < 19.5) return '#0284c7';      // Plateau average (Haveli/Shirur)
      if (rain < 21.5) return '#4f46e5';
      return '#1e1b4b';                       // Western Ghats crest (Mawal/Mulshi/Velhe/Bhor)
    } else {
      if (rain < 16.5) return '#7dd3fc';      // Rain-shadow dry (Malegaon/Deola)
      if (rain < 20.0) return '#38bdf8';
      if (rain < 23.5) return '#0284c7';      // Plateau average (Niphad/Sinnar)
      if (rain < 26.0) return '#4f46e5';
      return '#1e1b4b';                       // Sahyadri crest high-rain (Igatpuri/Trimbak/Peth)
    }
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
    const isSelected = props.panchayat_id === selectedPanchayatId;

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

  return (
    <div className="map-viewport-wrapper">
      {/* Floating View Mode Switcher */}
      <div className="map-floating-controls">
        <div className="toggle-group glass-panel">
          <button
            className={`toggle-btn ${viewMode === 'downscaled' ? 'active' : ''}`}
            onClick={() => setViewMode('downscaled')}
          >
            ✨ Disaggregated Panchayat (After)
          </button>
          <button
            className={`toggle-btn ${viewMode === 'block' ? 'active' : ''}`}
            onClick={() => setViewMode('block')}
          >
            📦 Coarse Block Mean (Before)
          </button>
          <button
            className={`toggle-btn ${viewMode === 'uncertainty' ? 'active' : ''}`}
            onClick={() => setViewMode('uncertainty')}
          >
            🛡️ Layer D Ensemble Confidence
          </button>
        </div>
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
        <MapController center={center} zoom={zoom} geojsonLayer={geojsonLayer} />
        {/* Dark-styled OpenStreetMap Base Layer */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          className="dark-tiles"
        />

        {geojsonLayer && (
          <GeoJSON
            key={`${district}-${viewMode}-${selectedPanchayatId}`}
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
              <span>{district === 'Pune' ? '< 14.5 mm (Dry East)' : '< 16.5 mm (Dry Plateau)'}</span>
              <span>{blockMean.toFixed(1)} mm (Mean)</span>
              <span>{district === 'Pune' ? '> 21.5 mm (Sahyadri)' : '> 26.0 mm (Ghats Crest)'}</span>
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
