import React, { useState, useEffect } from 'react';
import { History, Shield, CheckCircle, Edit, AlertOctagon, UserCheck } from 'lucide-react';

export default function FeedbackAuditView() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/feedback-log')
      .then(res => res.json())
      .then(data => {
        setLogs(data.logs || []);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  return (
    <div style={{ padding: '28px', maxWidth: '1200px', margin: '0 auto', overflowY: 'auto', height: 'calc(100vh - 64px)' }}>
      {/* Top Banner */}
      <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px', background: 'linear-gradient(135deg, rgba(15,23,42,0.9), rgba(99,102,241,0.12))', borderLeft: '4px solid #6366f1' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <History size={24} color="#818cf8" />
          <h2 style={{ fontSize: '22px', fontWeight: '800', color: '#ffffff' }}>
            DAMU Officer Review & MLOps Feedback Audit Trail
          </h2>
        </div>
        <p style={{ fontSize: '14px', color: '#cbd5e1', marginTop: '6px', lineHeight: '1.5' }}>
          Real-time operational logging of agromet officer overrides, dosage edits, and authorization decisions. This feedback loop feeds future retraining of Layer B models.
        </p>
      </div>

      {loading ? (
        <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
          Loading audit trail records...
        </div>
      ) : logs.length === 0 ? (
        <div className="glass-panel" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
          <UserCheck size={36} style={{ margin: '0 auto 10px auto', color: '#38bdf8' }} />
          <h4>No Officer Overrides Logged Yet</h4>
          <p style={{ fontSize: '13px', marginTop: '6px' }}>
            Open any panchayat from the Map Dashboard and click <strong>"Review & Edit"</strong> to record a live DAMU validation action.
          </p>
        </div>
      ) : (
        <div className="glass-panel" style={{ overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', textAlign: 'left' }}>
            <thead>
              <tr style={{ background: 'rgba(0,0,0,0.4)', borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)' }}>
                <th style={{ padding: '14px 16px' }}>Timestamp</th>
                <th style={{ padding: '14px 16px' }}>Officer ID</th>
                <th style={{ padding: '14px 16px' }}>Panchayat</th>
                <th style={{ padding: '14px 16px' }}>Action Type</th>
                <th style={{ padding: '14px 16px' }}>Modified Value / Content</th>
                <th style={{ padding: '14px 16px' }}>Officer Justification</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((entry, idx) => (
                <tr key={entry.log_id || idx} style={{ borderBottom: '1px solid var(--border-subtle)', transition: 'background 0.2s ease' }}>
                  <td style={{ padding: '14px 16px', color: 'var(--text-dim)', whiteSpace: 'nowrap' }}>
                    {new Date(entry.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  </td>
                  <td style={{ padding: '14px 16px', fontWeight: '600', color: '#38bdf8' }}>
                    {entry.officer_id}
                  </td>
                  <td style={{ padding: '14px 16px', fontWeight: '600', color: '#ffffff' }}>
                    {entry.panchayat_id}
                  </td>
                  <td style={{ padding: '14px 16px' }}>
                    <span className={`badge ${entry.action_type === 'APPROVE' ? 'badge-green' : entry.action_type === 'EDIT_ADVISORY' ? 'badge-yellow' : 'badge-blue'}`}>
                      {entry.action_type}
                    </span>
                  </td>
                  <td style={{ padding: '14px 16px', color: '#e2e8f0', maxWidth: '300px' }}>
                    <div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {entry.modified_value || '—'}
                    </div>
                  </td>
                  <td style={{ padding: '14px 16px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                    {entry.edit_reason}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
