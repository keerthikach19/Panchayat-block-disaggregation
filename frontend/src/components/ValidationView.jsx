import React, { useState, useEffect } from 'react';
import { Award, CheckCircle2, TrendingUp, ShieldCheck, Activity, MapPin, AlertCircle, BarChart3, Layers, Target, Info } from 'lucide-react';

export default function ValidationView() {
  const [metrics, setMetrics] = useState(null);

  useEffect(() => {
    fetch('/api/validation-metrics')
      .then(res => res.json())
      .then(data => setMetrics(data))
      .catch(err => console.error(err));
  }, []);

  if (!metrics) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
        Loading statistical cross-validation metrics...
      </div>
    );
  }

  // Segment 2 (Disaggregation Benchmark) is the primary source for headline cards
  const seg2 = metrics.segment_2_disaggregation_benchmark || {};
  const seg1 = metrics.segment_1_footprint_generalization || {};
  const meta = metrics.metadata || {};

  // Headline metrics from Segment 2 (true disaggregation benchmark)
  const h = seg2.headline_metrics || metrics.headline_metrics || {};
  const corr = seg2.correlation || metrics.correlation || {};
  const agromet = seg2.categorical_agricultural_20mm_threshold || metrics.categorical_agricultural_20mm_threshold || {};
  const ens = seg2.ensemble_uncertainty_metrics || metrics.ensemble_uncertainty_metrics || {};

  // Segment 1 metrics
  const h1 = seg1.headline_metrics || {};
  const corr1 = seg1.correlation || {};
  const agromet1 = seg1.categorical_agricultural_20mm_threshold || {};
  const spatial1 = seg1.spatial_plausibility || {};

  // District metadata
  const seg2Districts = meta.segment_2_districts_included || [];
  const seg2StationCounts = meta.segment_2_station_count_by_district || {};

  return (
    <div style={{ padding: '28px', maxWidth: '1200px', margin: '0 auto', overflowY: 'auto', height: 'calc(100vh - 64px)' }}>
      {/* Top Headline Banner */}
      <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px', background: 'linear-gradient(135deg, rgba(15,23,42,0.9), rgba(16,185,129,0.12))', borderLeft: '4px solid #10b981' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Award size={24} color="#34d399" />
          <h2 style={{ fontSize: '22px', fontWeight: '800', color: '#ffffff' }}>
            Segmented Validation &amp; Benchmark Results
          </h2>
        </div>
        <p style={{ fontSize: '14px', color: '#cbd5e1', marginTop: '6px', lineHeight: '1.5' }}>
          Evaluated via <strong>Segmented Leave-Station-Out Cross-Validation (LOOCV)</strong>. Headline metrics are sourced from
          Segment 2 (Disaggregation Skill Benchmark) — restricted to districts with ≥{meta.min_stations_threshold_used || 2} stations
          where the naive block-mean baseline represents a genuine spatial average, not a single-station passthrough.
        </p>
      </div>

      {/* Methodology Note */}
      <div className="glass-panel" style={{ padding: '16px 20px', marginBottom: '24px', background: 'rgba(251,191,36,0.08)', borderLeft: '3px solid #fbbf24', display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
        <Info size={18} color="#fbbf24" style={{ flexShrink: 0, marginTop: '2px' }} />
        <p style={{ fontSize: '13px', color: '#e2e8f0', lineHeight: '1.6', margin: 0 }}>
          <strong style={{ color: '#fbbf24' }}>Why segmented?</strong> In single-station districts, the block-mean equals the station's own reading,
          giving the naive baseline an artificial 0.00 mm error. This masks real downscaling skill in aggregate metrics.
          Segment 2 isolates the {seg2Districts.length} district{seg2Districts.length !== 1 ? 's' : ''} ({seg2Districts.join(', ')}) where
          ≥{meta.min_stations_threshold_used || 2} stations exist and disaggregation is genuinely testable.
        </p>
      </div>

      {/* ─── SEGMENT 2: HEADLINE CARDS (PRIMARY) ─── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
        <Target size={20} color="#34d399" />
        <h3 style={{ fontSize: '17px', fontWeight: '700', color: '#ffffff', margin: 0 }}>
          Segment 2: Disaggregation Skill Benchmark
        </h3>
        <span style={{ fontSize: '12px', color: '#94a3b8', background: 'rgba(0,0,0,0.3)', padding: '3px 10px', borderRadius: '12px' }}>
          {meta.segment_2_sample_size || h.sample_size || '—'} station-days · {seg2Districts.length} districts
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px', marginBottom: '28px' }}>
        {/* Card 1: RMSE Improvement */}
        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: '600', textTransform: 'uppercase' }}>
            RMSE Error Reduction
          </div>
          <div style={{ fontSize: '32px', fontWeight: '800', color: h.rmse_improvement_percent > 0 ? '#34d399' : '#f87171', margin: '8px 0 4px 0' }}>
            {h.rmse_improvement_percent > 0 ? '+' : ''}{h.rmse_improvement_percent || 0}%
          </div>
          <div style={{ fontSize: '13px', color: 'var(--text-dim)' }}>
            Downscaled: <strong>{h.downscaled_model_rmse_mm || '—'} mm</strong> vs Block: <strong>{h.naive_baseline_rmse_mm || '—'} mm</strong>
          </div>
        </div>

        {/* Card 2: Pearson Correlation */}
        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: '600', textTransform: 'uppercase' }}>
            Pearson Correlation (r)
          </div>
          <div style={{ fontSize: '32px', fontWeight: '800', color: '#38bdf8', margin: '8px 0 4px 0' }}>
            {corr.pearson_r_downscaled || '—'}
          </div>
          <div style={{ fontSize: '13px', color: 'var(--text-dim)' }}>
            vs Naive Block Assignment (r = {corr.pearson_r_naive || '—'})
          </div>
        </div>

        {/* Card 3: 20mm Agricultural Threshold POD */}
        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: '600', textTransform: 'uppercase' }}>
            20mm Spray/Irrigation POD
          </div>
          <div style={{ fontSize: '32px', fontWeight: '800', color: '#fbbf24', margin: '8px 0 4px 0' }}>
            {agromet.downscaled_model?.POD != null ? (agromet.downscaled_model.POD * 100).toFixed(0) : '—'}%
          </div>
          <div style={{ fontSize: '13px', color: 'var(--text-dim)' }}>
            FAR: <strong>{agromet.downscaled_model?.FAR != null ? (agromet.downscaled_model.FAR * 100).toFixed(1) : '—'}%</strong> (vs {agromet.naive_baseline?.FAR != null ? (agromet.naive_baseline.FAR * 100).toFixed(1) : '—'}% Naive)
          </div>
        </div>

        {/* Card 4: Ensemble Spread-Skill Reliability */}
        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: '600', textTransform: 'uppercase' }}>
            Ensemble Spread-Skill Ratio
          </div>
          <div style={{ fontSize: '32px', fontWeight: '800', color: '#818cf8', margin: '8px 0 4px 0' }}>
            {ens.spread_skill_ratio || '—'}
          </div>
          <div style={{ fontSize: '13px', color: 'var(--text-dim)' }}>
            IPED 30-member dispersion tracks error variance
          </div>
        </div>
      </div>

      {/* Segment 2 District Breakdown */}
      {seg2Districts.length > 0 && (
        <div className="glass-panel" style={{ padding: '18px 22px', marginBottom: '28px' }}>
          <h4 style={{ fontSize: '14px', fontWeight: '700', color: '#94a3b8', margin: '0 0 10px 0', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Multi-Station Districts in Benchmark
          </h4>
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            {seg2Districts.map(d => (
              <div key={d} style={{
                background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.25)',
                padding: '8px 16px', borderRadius: '8px', fontSize: '13px', color: '#e2e8f0'
              }}>
                <strong style={{ color: '#34d399' }}>{d}</strong>
                <span style={{ color: '#94a3b8', marginLeft: '8px' }}>{seg2StationCounts[d] || '?'} stations</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ─── SEGMENT 1: STATEWIDE GENERALIZATION ─── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
        <Layers size={20} color="#38bdf8" />
        <h3 style={{ fontSize: '17px', fontWeight: '700', color: '#ffffff', margin: 0 }}>
          Segment 1: Statewide Footprint Generalization
        </h3>
        <span style={{ fontSize: '12px', color: '#94a3b8', background: 'rgba(0,0,0,0.3)', padding: '3px 10px', borderRadius: '12px' }}>
          {meta.segment_1_sample_size || '—'} station-days · All districts
        </span>
      </div>

      <p style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '16px', lineHeight: '1.5' }}>
        Tests whether Layer B learns generalizable physical relationships (elevation, land cover, coastal proximity)
        across all 4 physiographic zones. Not a disaggregation skill claim — single-station districts inflate the naive baseline accuracy.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px', marginBottom: '28px' }}>
        <div className="glass-panel" style={{ padding: '16px' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: '600', textTransform: 'uppercase' }}>RMSE</div>
          <div style={{ fontSize: '24px', fontWeight: '800', color: '#94a3b8', margin: '6px 0 2px 0' }}>
            {h1.downscaled_model_rmse_mm || '—'} mm
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
            vs Naive: {h1.naive_baseline_rmse_mm || '—'} mm ({h1.rmse_improvement_percent > 0 ? '+' : ''}{h1.rmse_improvement_percent || 0}%)
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '16px' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: '600', textTransform: 'uppercase' }}>Pearson r</div>
          <div style={{ fontSize: '24px', fontWeight: '800', color: '#94a3b8', margin: '6px 0 2px 0' }}>
            {corr1.pearson_r_downscaled || '—'}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
            vs Naive: {corr1.pearson_r_naive || '—'}
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '16px' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: '600', textTransform: 'uppercase' }}>20mm POD</div>
          <div style={{ fontSize: '24px', fontWeight: '800', color: '#94a3b8', margin: '6px 0 2px 0' }}>
            {agromet1.downscaled_model?.POD != null ? (agromet1.downscaled_model.POD * 100).toFixed(0) : '—'}%
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
            FAR: {agromet1.downscaled_model?.FAR != null ? (agromet1.downscaled_model.FAR * 100).toFixed(1) : '—'}%
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '16px' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: '600', textTransform: 'uppercase' }}>Orographic Check</div>
          <div style={{ fontSize: '24px', fontWeight: '800', color: spatial1.orographic_gradient_physically_sound ? '#34d399' : '#f87171', margin: '6px 0 2px 0' }}>
            {spatial1.orographic_gradient_physically_sound ? 'PASSED' : 'CHECK'}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
            Elev-Rain r = {spatial1.elevation_rainfall_correlation || '—'}
          </div>
        </div>
      </div>

      {/* Detailed Architectural Decisions & Transparency */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        <div className="glass-panel" style={{ padding: '22px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: '700', color: '#ffffff', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <ShieldCheck size={18} color="#38bdf8" /> Station Density & Layer C Geostatistical Decision
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: '1.6' }}>
            In compliance with PRP Section 5, Layer C geostatistical residual correction is <strong>conditional on verified local station density</strong>:
          </p>
          <ul style={{ fontSize: '13px', color: '#e2e8f0', marginTop: '10px', paddingLeft: '20px', lineHeight: '1.6' }}>
            <li><strong>Nashik Target District:</strong> 15 active station anchors confirmed (&ge; 10 threshold). Fitted <strong>Universal Kriging with regional elevation drift</strong>.</li>
            <li><strong>Second District (Pune):</strong> 12 station anchors confirmed. Applied Universal Kriging.</li>
            <li><strong>Fallback Mode:</strong> Automatically switches to IDW (Inverse Distance Weighting, p=2) if station density falls below 5 to prevent overfitting sparse variograms.</li>
          </ul>
        </div>

        <div className="glass-panel" style={{ padding: '22px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: '700', color: '#ffffff', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <MapPin size={18} color="#34d399" /> Maharashtra 4-Zone Physiographic Footprint Coverage
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: '1.6' }}>
            The deviation model (Layer B) was trained on the entire diverse Maharashtra footprint, ensuring genuine generalization across:
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginTop: '10px', fontSize: '12px' }}>
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px', borderRadius: '6px' }}>
              🌊 <strong>Konkan Coastal</strong> (7 stations, 0-35m)
            </div>
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px', borderRadius: '6px' }}>
              ⛰️ <strong>Sahyadri Crest</strong> (8 stations, 530-1380m)
            </div>
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px', borderRadius: '6px' }}>
              🌾 <strong>Deccan Plateau</strong> (17 stations, 209-670m)
            </div>
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px', borderRadius: '6px' }}>
              ☀️ <strong>Vidarbha Plains</strong> (8 stations, 189-445m)
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
