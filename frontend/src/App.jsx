import React, { useState, useEffect } from 'react';
import { Map, BarChart2, History, CloudSun, Shield, RefreshCw, ChevronDown, Radio } from 'lucide-react';
import MapDashboard from './components/MapDashboard';
import ExplainabilityPanel from './components/ExplainabilityPanel';
import OfficerReviewModal from './components/OfficerReviewModal';
import DisseminationPreviewModal from './components/DisseminationPreviewModal';
import ValidationView from './components/ValidationView';
import FeedbackAuditView from './components/FeedbackAuditView';

export default function App() {
  const [activeTab, setActiveTab] = useState('map'); // 'map' | 'validation' | 'audit'
  const [selectedDistrict, setSelectedDistrict] = useState('Nashik');
  const [selectedPanchayatId, setSelectedPanchayatId] = useState(null);
  const [explainData, setExplainData] = useState(null);
  const [explainLoading, setExplainLoading] = useState(false);
  const [geojsonLayer, setGeojsonLayer] = useState(null);
  const [geojsonLoading, setGeojsonLoading] = useState(false);
  const [reviewModalAdvisory, setReviewModalAdvisory] = useState(null);
  const [disseminatePanchayatId, setDisseminatePanchayatId] = useState(null);

  // Fetch GeoJSON layer when district changes
  useEffect(() => {
    setGeojsonLayer(null);
    setExplainData(null);
    setSelectedPanchayatId(null);
    setGeojsonLoading(true);
    fetch(`/api/panchayats/geojson/${selectedDistrict.toLowerCase()}`)
      .then(res => {
        if (!res.ok) {
          throw new Error(`GeoJSON not available for ${selectedDistrict}`);
        }
        return res.json();
      })
      .then(data => {
        setGeojsonLayer(data);
        setGeojsonLoading(false);
        // Auto-select first panchayat
        if (data.features && data.features.length > 0) {
          const firstId = data.features[0].properties.panchayat_id;
          handleSelectPanchayat(firstId);
        }
      })
      .catch(err => {
        console.error('Failed to load GeoJSON layer:', err);
        setGeojsonLayer(null);
        setGeojsonLoading(false);
      });
  }, [selectedDistrict]);


  const handleSelectPanchayat = (panchayatId) => {
    setSelectedPanchayatId(panchayatId);
    setExplainLoading(true);
    fetch(`/api/panchayat/${panchayatId}/explainability`)
      .then(res => res.json())
      .then(data => {
        setExplainData(data);
        setExplainLoading(false);
      })
      .catch(err => {
        console.error('Failed to load explainability:', err);
        setExplainLoading(false);
      });
  };

  return (
    <div className="app-shell">
      {/* Top Header Navigation */}
      <header className="top-nav">
        <div className="nav-brand">
          <div className="nav-logo-badge">IMD DAMU</div>
          <div>
            <div style={{ fontSize: '15px', fontWeight: '800', color: '#ffffff', letterSpacing: '-0.2px' }}>
              Gramin Krishi Mausam Sewa (GKMS)
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              Block-to-Panchayat Physical Weather Downscaling & Advisory Engine
            </div>
          </div>
        </div>

        {/* District Switcher (Scalability Proof) */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>District Extent:</span>
          <select
            value={selectedDistrict}
            onChange={(e) => setSelectedDistrict(e.target.value)}
            style={{
              background: 'rgba(15, 23, 42, 0.9)',
              color: '#38bdf8',
              border: '1px solid var(--border-active)',
              padding: '6px 12px',
              borderRadius: '8px',
              fontWeight: '700',
              fontSize: '13px',
              cursor: 'pointer'
            }}
          >
            <option value="Nashik">📍 Nashik (Target Demo - Extreme Gradient)</option>
            <option value="Pune">📍 Pune (Multi-District Scalability Proof)</option>
          </select>
        </div>

        {/* Navigation Tabs */}
        <nav className="nav-tabs">
          <button
            className={`nav-tab-btn ${activeTab === 'map' ? 'active' : ''}`}
            onClick={() => setActiveTab('map')}
          >
            <Map size={16} /> Live Disaggregation Map
          </button>
          <button
            className={`nav-tab-btn ${activeTab === 'validation' ? 'active' : ''}`}
            onClick={() => setActiveTab('validation')}
          >
            <BarChart2 size={16} /> Statistical Validation Suite
          </button>
          <button
            className={`nav-tab-btn ${activeTab === 'audit' ? 'active' : ''}`}
            onClick={() => setActiveTab('audit')}
          >
            <History size={16} /> DAMU MLOps Audit Trail
          </button>
        </nav>
      </header>

      {/* Main Content Workspace */}
      {activeTab === 'map' && (
        <main className="main-workspace">
          <MapDashboard
            district={selectedDistrict}
            onSelectPanchayat={handleSelectPanchayat}
            selectedPanchayatId={selectedPanchayatId}
            geojsonLayer={geojsonLayer}
            loading={geojsonLoading}
          />
          <ExplainabilityPanel
            explainData={explainData}
            loading={explainLoading}
            onOpenReviewModal={(adv) => setReviewModalAdvisory(adv)}
            onOpenDisseminateModal={(pId) => setDisseminatePanchayatId(pId)}
          />
        </main>
      )}


      {activeTab === 'validation' && (
        <ValidationView />
      )}

      {activeTab === 'audit' && (
        <FeedbackAuditView />
      )}

      {/* Officer Review Dialog Modal */}
      {reviewModalAdvisory && (
        <OfficerReviewModal
          advisory={reviewModalAdvisory}
          onClose={() => setReviewModalAdvisory(null)}
          onSaveReview={() => {
            // Re-fetch explainability
            if (selectedPanchayatId) handleSelectPanchayat(selectedPanchayatId);
          }}
        />
      )}

      {/* Farmer Dissemination Simulation Modal */}
      {disseminatePanchayatId && (
        <DisseminationPreviewModal
          panchayatId={disseminatePanchayatId}
          onClose={() => setDisseminatePanchayatId(null)}
        />
      )}
    </div>
  );
}
