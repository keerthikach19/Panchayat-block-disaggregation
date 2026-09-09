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
  const [forecastMeta, setForecastMeta] = useState(null);
  const [reviewModalAdvisory, setReviewModalAdvisory] = useState(null);
  const [disseminatePanchayatId, setDisseminatePanchayatId] = useState(null);

  const [retryNotice, setRetryNotice] = useState(null);

  // Fetch GeoJSON layer when district changes (with auto-retry if backend is booting)
  useEffect(() => {
    let timer = null;
    let isMounted = true;

    const loadData = () => {
      setGeojsonLayer(null);
      setExplainData(null);
      setSelectedPanchayatId(null);
      setGeojsonLoading(true);
      setForecastMeta(null);

      fetch(`/api/forecast/${selectedDistrict.toLowerCase()}`)
        .then(res => {
          if (res.status === 503) {
            throw new Error('Backend initializing');
          }
          if (!res.ok) {
            throw new Error(`Live forecast not available for ${selectedDistrict}`);
          }
          return res.json();
        })
        .then(forecast => {
          if (!isMounted) return;
          setForecastMeta(forecast);
          setRetryNotice(null);
          return fetch(`/api/panchayats/geojson/${selectedDistrict.toLowerCase()}`);
        })
        .then(res => {
          if (!res || !isMounted) return;
          if (!res.ok) throw new Error(`GeoJSON not available for ${selectedDistrict}`);
          return res.json();
        })
        .then(data => {
          if (!data || !isMounted) return;
          setGeojsonLayer(data);
          setGeojsonLoading(false);
          setRetryNotice(null);
          if (data.features && data.features.length > 0) {
            const firstId = data.features[0].properties.panchayat_id;
            handleSelectPanchayat(firstId);
          }
        })
        .catch(err => {
          if (!isMounted) return;
          console.warn('Backend connection pending:', err.message);
          setRetryNotice('Backend server initializing on port 8000... Retrying in 2s');
          timer = setTimeout(() => {
            if (isMounted) loadData();
          }, 2500);
        });
    };

    loadData();

    return () => {
      isMounted = false;
      if (timer) clearTimeout(timer);
    };
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
        <div className="nav-left">
          <div className="nav-brand">
            <div className="nav-brand-title">
              GKMS Weather Downscaling
            </div>
          </div>

          {/* Compact Live Indicator */}
          <div className="nav-badges">
            <span className="nav-badge-live">
              <span className="live-dot"></span> IMD Live Feed
            </span>
            {retryNotice && (
              <span style={{ fontSize: '11px', color: '#f59e0b', display: 'inline-flex', alignItems: 'center', gap: '6px', background: 'rgba(245,158,11,0.15)', padding: '3px 8px', borderRadius: '4px', border: '1px solid rgba(245,158,11,0.4)' }}>
                <RefreshCw size={11} className="animate-spin" /> {retryNotice}
              </span>
            )}
          </div>

          {/* District Switcher */}
          <div className="nav-district-select">
            <select
              value={selectedDistrict}
              onChange={(e) => setSelectedDistrict(e.target.value)}
            >
              <option value="Nashik">📍 Nashik</option>
              <option value="Pune">📍 Pune</option>
            </select>
            <ChevronDown size={14} className="select-chevron" />
          </div>
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
            forecastMeta={forecastMeta}
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
