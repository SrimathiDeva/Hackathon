import React, { useState, useEffect } from 'react'
import { RefreshCw } from 'lucide-react'
import { fetchProtocol } from '../api'
import type { ProtocolInfo } from '../types'

export const ProtocolView: React.FC = () => {
  const [data, setData] = useState<ProtocolInfo | null>(null)

  useEffect(() => {
    fetchProtocol()
      .then((res) => {
        setData(res)
      })
      .catch(() => {})
  }, [])

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '2.5rem' }}>
      {/* Header */}
      <div>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
          <span className="badge badge-cyan">Trial Progression & Versioning</span>
        </div>
        <h1 style={{ fontSize: '2.25rem', fontWeight: 800, color: '#f8fafc', marginBottom: '0.4rem' }}>
          Protocol Timeline & Study Cuts
        </h1>
        <p style={{ color: '#94a3b8', fontSize: '1.05rem', maxWidth: '820px', lineHeight: 1.5 }}>
          Clinical studies progress through database cuts and protocol amendments. StudyGraph dynamically adapts its visit window rules and applies field corrections for any requested cut.
        </p>
      </div>

      {/* Horizontal Phase Timeline */}
      <div className="glass-card" style={{ padding: '2rem' }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#f8fafc', marginBottom: '1.5rem' }}>
          Protocol Amendment Phases
        </h2>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
            gap: '1.25rem',
            position: 'relative',
          }}
        >
          {/* Phase 1 */}
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.8)',
              border: '1px solid rgba(56, 189, 248, 0.25)',
              borderRadius: '12px',
              padding: '1.5rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.75rem',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span className="badge badge-cyan">Cuts 1–4</span>
              <span className="badge badge-indigo font-mono">Protocol v1</span>
            </div>
            <div style={{ fontSize: '1.3rem', fontWeight: 700, color: '#f8fafc' }}>
              ±7 Day Visit Window
            </div>
            <p style={{ fontSize: '0.85rem', color: '#94a3b8', lineHeight: 1.5 }}>
              Original protocol specification providing a standard allowable window of ±7 days around scheduled clinical visits for procedure and lab compliance.
            </p>
            <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: 'auto', paddingTop: '0.5rem', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
              Applicable for questions evaluated during Cuts 1 to 4.
            </div>
          </div>

          {/* Phase 2 */}
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.8)',
              border: '1px solid rgba(245, 158, 11, 0.3)',
              borderRadius: '12px',
              padding: '1.5rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.75rem',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span className="badge badge-amber">Cuts 5–8</span>
              <span className="badge badge-indigo font-mono">Amendment 2</span>
            </div>
            <div style={{ fontSize: '1.3rem', fontWeight: 700, color: '#f8fafc' }}>
              ±3 Day Visit Window
            </div>
            <p style={{ fontSize: '0.85rem', color: '#94a3b8', lineHeight: 1.5 }}>
              Amendment 2 tightened the window to ±3 days to improve data precision. Cut 5 also delivers <strong>200 re-issued central laboratory values</strong> from corrections.csv.
            </p>
            <div style={{ fontSize: '0.75rem', color: '#fbbf24', marginTop: 'auto', paddingTop: '0.5rem', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
              ★ 200 central lab corrections applied at Cut 5.
            </div>
          </div>

          {/* Phase 3 */}
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.8)',
              border: '1px solid rgba(52, 211, 153, 0.25)',
              borderRadius: '12px',
              padding: '1.5rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.75rem',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span className="badge badge-emerald">Cuts 9–12</span>
              <span className="badge badge-indigo font-mono">Protocol v3</span>
            </div>
            <div style={{ fontSize: '1.3rem', fontWeight: 700, color: '#f8fafc' }}>
              Cut-Dependent Protocol Rules
            </div>
            <p style={{ fontSize: '0.85rem', color: '#94a3b8', lineHeight: 1.5 }}>
              Study progression incorporating final monitoring cuts, late visit windows, and protocol lock provisions.
            </p>
            <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: 'auto', paddingTop: '0.5rem', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
              Dynamically reads allowable windows when specified.
            </div>
          </div>
        </div>
      </div>

      {/* Dynamic Graph Rebuilding Callout */}
      <div
        className="glass-card"
        style={{
          padding: '1.75rem',
          background: 'linear-gradient(135deg, rgba(14, 165, 233, 0.08) 0%, rgba(15, 23, 42, 0.8) 100%)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', marginBottom: '0.5rem' }}>
          <RefreshCw size={20} color="#38bdf8" />
          <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#f8fafc' }}>
            Mid-Study Graph Rebuild Support
          </h3>
        </div>
        <p style={{ fontSize: '0.9rem', color: '#94a3b8', lineHeight: 1.6, maxWidth: '850px' }}>
          <code>StudyGraph.build(cut=N)</code> reconstructs the study state at any point in the trial history without restarting Python processes. When answering questions without an explicit number of days (e.g. general allowable visit window), <code>graph.current_cut</code> ensures that the exact rule in force is applied.
        </p>
      </div>

      {/* Detailed 12-Cut Reference Table */}
      <div className="glass-card" style={{ padding: '1.75rem', overflowX: 'auto' }}>
        <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#f8fafc', marginBottom: '1rem' }}>
          Database Cut History (12 Trial Cuts)
        </h3>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.88rem' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)', color: '#94a3b8' }}>
              <th style={{ padding: '0.7rem' }}>Cut</th>
              <th style={{ padding: '0.7rem' }}>Protocol Version</th>
              <th style={{ padding: '0.7rem' }}>Allowable Visit Window</th>
              <th style={{ padding: '0.7rem' }}>Field Corrections</th>
              <th style={{ padding: '0.7rem' }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {data?.details.map((c) => (
              <tr key={c.cut} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                <td style={{ padding: '0.7rem', fontWeight: 700, color: '#38bdf8', fontFamily: 'var(--font-mono)' }}>
                  Cut {c.cut}
                </td>
                <td style={{ padding: '0.7rem', color: '#f8fafc' }}>v{c.version}</td>
                <td style={{ padding: '0.7rem', color: '#cbd5e1' }}>{c.window}</td>
                <td style={{ padding: '0.7rem' }}>
                  {c.corrections > 0 ? (
                    <span className="badge badge-amber font-mono">{c.corrections} corrections</span>
                  ) : (
                    <span style={{ color: '#64748b' }}>0</span>
                  )}
                </td>
                <td style={{ padding: '0.7rem' }}>
                  <span className="badge badge-emerald">Ingested</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
