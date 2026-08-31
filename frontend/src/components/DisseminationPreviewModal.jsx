import React, { useState, useEffect } from 'react';
import { X, Smartphone, MessageSquare, Bell, Globe } from 'lucide-react';

export default function DisseminationPreviewModal({ panchayatId, onClose }) {
  const [channel, setChannel] = useState('WhatsApp'); // 'WhatsApp' | 'SMS' | 'mKisan'
  const [language, setLanguage] = useState('mr'); // 'mr' | 'en'
  const [previewText, setPreviewText] = useState('Loading farmer advisory preview...');
  const [panchayatName, setPanchayatName] = useState('Gram Panchayat');

  useEffect(() => {
    if (!panchayatId) return;

    fetch('/api/disseminate/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        panchayat_id: panchayatId,
        channel: channel,
        language: language
      })
    })
      .then(res => res.json())
      .then(data => {
        setPreviewText(data.rendered_preview);
        setPanchayatName(data.panchayat_name);
      })
      .catch(err => console.error(err));
  }, [panchayatId, channel, language]);

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{ maxWidth: '520px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <div style={{ fontSize: '11px', color: '#38bdf8', fontWeight: '700', textTransform: 'uppercase' }}>
              Farmer Dissemination Simulation
            </div>
            <h3 style={{ fontSize: '18px', color: '#ffffff' }}>
              Broadcast Preview: {panchayatName}
            </h3>
          </div>
          <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
            <X size={20} />
          </button>
        </div>

        {/* Channel and Language Selectors */}
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', marginBottom: '16px' }}>
          <div className="toggle-group" style={{ flex: 1 }}>
            <button className={`toggle-btn ${channel === 'WhatsApp' ? 'active' : ''}`} onClick={() => setChannel('WhatsApp')}>
              WhatsApp
            </button>
            <button className={`toggle-btn ${channel === 'SMS' ? 'active' : ''}`} onClick={() => setChannel('SMS')}>
              SMS
            </button>
            <button className={`toggle-btn ${channel === 'mKisan' ? 'active' : ''}`} onClick={() => setChannel('mKisan')}>
              mKisan Portal
            </button>
          </div>

          <div className="toggle-group">
            <button className={`toggle-btn ${language === 'mr' ? 'active' : ''}`} onClick={() => setLanguage('mr')}>
              मराठी
            </button>
            <button className={`toggle-btn ${language === 'en' ? 'active' : ''}`} onClick={() => setLanguage('en')}>
              English
            </button>
          </div>
        </div>

        {/* Mocked Mobile Preview Container */}
        <div style={{
          background: channel === 'WhatsApp' ? '#075e54' : '#0f172a',
          padding: '16px',
          borderRadius: '16px',
          border: '1px solid var(--border-subtle)',
          boxShadow: 'inset 0 2px 10px rgba(0,0,0,0.5)'
        }}>
          {channel === 'WhatsApp' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px', color: '#dcf8c6', fontSize: '12px' }}>
              <MessageSquare size={14} /> <strong>IMD DAMU KVK Nashik Official Broadcast</strong>
            </div>
          )}

          <div style={{
            background: channel === 'WhatsApp' ? '#128c7e' : '#1e293b',
            color: '#f8fafc',
            padding: '14px',
            borderRadius: '10px',
            fontSize: '13px',
            lineHeight: '1.6',
            whiteSpace: 'pre-line',
            fontFamily: language === 'mr' ? "'Inter', sans-serif" : 'monospace'
          }}>
            {previewText}
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '10px', fontSize: '11px', color: 'rgba(255,255,255,0.6)' }}>
            <span>Target: Registered Farmers in {panchayatName}</span>
            <span>Status: Verified by DAMU</span>
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '16px' }}>
          <button className="btn-secondary" onClick={onClose}>
            Close Preview
          </button>
        </div>
      </div>
    </div>
  );
}
