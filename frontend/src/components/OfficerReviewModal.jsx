import React, { useState } from 'react';
import { CheckCircle, AlertCircle, X, ShieldAlert, FileEdit, Send } from 'lucide-react';

export default function OfficerReviewModal({ advisory, onClose, onSaveReview }) {
  const [officerId, setOfficerId] = useState('DAMU_OFFICER_NASHIK_01');
  const [actionType, setActionType] = useState('APPROVE'); // 'APPROVE' | 'EDIT_ADVISORY' | 'OVERRIDE_FORECAST'
  const [editedText, setEditedText] = useState(advisory?.agromet_advisory_en || '');
  const [overrideRain, setOverrideRain] = useState(advisory?.downscaled_weather?.rainfall_mm || 22.5);
  const [reason, setReason] = useState('Verified against DAMU KVK Nashik automatic weather gauge network.');
  const [submitting, setSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');

  if (!advisory) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);

    const payload = {
      officer_id: officerId,
      panchayat_id: advisory.panchayat_id,
      action_type: actionType,
      field_modified: actionType === 'OVERRIDE_FORECAST' ? 'downscaled_rain_pred' : 'agromet_advisory_en',
      original_value: actionType === 'OVERRIDE_FORECAST' ? `${advisory.downscaled_weather?.rainfall_mm} mm` : advisory.agromet_advisory_en,
      modified_value: actionType === 'OVERRIDE_FORECAST' ? `${overrideRain} mm` : editedText,
      edit_reason: reason
    };

    try {
      const res = await fetch(`/api/advisory/${advisory.panchayat_id}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      setSuccessMsg(`Advisory successfully recorded as '${actionType}' by Officer ${officerId}`);
      if (onSaveReview) onSaveReview(data.log_entry);
      setTimeout(() => {
        onClose();
      }, 1400);
    } catch (err) {
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <div style={{ fontSize: '12px', color: '#38bdf8', fontWeight: '700', textTransform: 'uppercase' }}>
              IMD DAMU Operational Review Workflow
            </div>
            <h3 style={{ fontSize: '18px', color: '#ffffff', marginTop: '2px' }}>
              Review Bulletin: {advisory.panchayat_name} ({advisory.block_name})
            </h3>
          </div>
          <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
            <X size={20} />
          </button>
        </div>

        {successMsg ? (
          <div style={{ padding: '30px', textAlign: 'center', color: '#34d399' }}>
            <CheckCircle size={40} style={{ margin: '0 auto 12px auto' }} />
            <h4>{successMsg}</h4>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '6px' }}>
              Action recorded in MLOps feedback log table.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* Officer Identification */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  DAMU Officer ID:
                </label>
                <input
                  type="text"
                  value={officerId}
                  onChange={(e) => setOfficerId(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', background: '#1e293b', border: '1px solid var(--border-subtle)', borderRadius: '6px', color: '#fff', fontSize: '13px' }}
                />
              </div>
              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  Review Action:
                </label>
                <select
                  value={actionType}
                  onChange={(e) => setActionType(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', background: '#1e293b', border: '1px solid var(--border-subtle)', borderRadius: '6px', color: '#fff', fontSize: '13px' }}
                >
                  <option value="APPROVE">Approve & Authorize for Dissemination</option>
                  <option value="EDIT_ADVISORY">Edit Advisory Text / Dosage</option>
                  <option value="OVERRIDE_FORECAST">Override Precipitation Prediction</option>
                  <option value="REJECT">Reject Bulletin</option>
                </select>
              </div>
            </div>

            {/* Editable Fields based on Action Type */}
            {actionType === 'EDIT_ADVISORY' && (
              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  Modified Agromet Advisory Text (English):
                </label>
                <textarea
                  rows={4}
                  value={editedText}
                  onChange={(e) => setEditedText(e.target.value)}
                  style={{ width: '100%', padding: '10px', background: '#1e293b', border: '1px solid var(--border-active)', borderRadius: '6px', color: '#fff', fontSize: '13px', lineHeight: '1.5' }}
                />
              </div>
            )}

            {actionType === 'OVERRIDE_FORECAST' && (
              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  Override Rainfall Value (mm):
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={overrideRain}
                  onChange={(e) => setOverrideRain(parseFloat(e.target.value))}
                  style={{ width: '100%', padding: '8px 12px', background: '#1e293b', border: '1px solid var(--border-active)', borderRadius: '6px', color: '#fff', fontSize: '14px', fontWeight: '700' }}
                />
              </div>
            )}

            {/* Mandatory Reason for MLOps Audit Trail */}
            <div>
              <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                Officer Justification & Field Evidence (MLOps Audit Log):
              </label>
              <input
                type="text"
                required
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="E.g., Verified with local KVK Nashik automatic weather station"
                style={{ width: '100%', padding: '8px 12px', background: '#1e293b', border: '1px solid var(--border-subtle)', borderRadius: '6px', color: '#fff', fontSize: '13px' }}
              />
            </div>

            {/* Action Buttons */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
              <button type="button" className="btn-secondary" onClick={onClose}>
                Cancel
              </button>
              <button type="submit" className="btn-primary" disabled={submitting}>
                {submitting ? 'Recording Action...' : 'Save & Authorize Advisory'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
