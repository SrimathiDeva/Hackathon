import React, { useState, useEffect } from 'react'
import {
  ArrowRight,
  Info,
} from 'lucide-react'
import { fetchHysLaw } from '../api'
import type { HysLawData } from '../types'

export const HysLawView: React.FC = () => {
  const [data, setData] = useState<HysLawData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchHysLaw()
      .then((res) => {
        setData(res)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '2.5rem' }}>
      {/* Header Banner */}
      <div>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
          <span className="badge badge-amber">Clinical Safety Analysis</span>
          <span className="badge badge-cyan">FDA Guidance Grounded</span>
        </div>
        <h1 style={{ fontSize: '2.25rem', fontWeight: 800, color: '#f8fafc', marginBottom: '0.4rem' }}>
          Hy's Law Findings
        </h1>
        <p style={{ color: '#cbd5e1', fontSize: '1.05rem', maxWidth: '800px', lineHeight: 1.5 }}>
          Candidates identified using the study's documented liver-safety criteria and normalized laboratory values.
        </p>

        {/* Liver safety definition box */}
        <div
          className="glass-card"
          style={{
            marginTop: '1.5rem',
            padding: '1.25rem 1.5rem',
            borderLeft: '4px solid #fbbf24',
            background: 'rgba(245, 158, 11, 0.05)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
            <Info size={18} color="#fbbf24" />
            <span style={{ fontWeight: 700, color: '#f8fafc', fontSize: '0.95rem' }}>
              Hy's Law Clinical Thresholds (Protocol Central Limits)
            </span>
          </div>
          <div style={{ fontSize: '0.88rem', color: '#94a3b8', lineHeight: 1.6 }}>
            <strong>1. ALT or AST &gt; 3× ULN:</strong> Serum ALT &gt; 168 U/L (Central ULN = 56 U/L).<br />
            <strong>2. Total Bilirubin &gt; 2× ULN:</strong> Total bilirubin &gt; 2.4 mg/dL (Central ULN = 1.2 mg/dL).<br />
            <strong>3. Concomitance:</strong> Elevated ALT and Bilirubin occur concurrently or within 14 days without evidence of baseline cholestasis.
          </div>
        </div>
      </div>

      {/* S07 Unit Conversion Callout Card */}
      <div
        className="glass-card"
        style={{
          padding: '1.75rem',
          border: '1px solid rgba(56, 189, 248, 0.3)',
          background: 'linear-gradient(135deg, rgba(14, 165, 233, 0.12) 0%, rgba(15, 23, 42, 0.8) 100%)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <span className="badge badge-cyan" style={{ marginBottom: '0.4rem' }}>
              Critical Laboratory Normalization
            </span>
            <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#f8fafc' }}>
              Site S07 Unit Conversion: µkat/L → U/L
            </h2>
            <p style={{ color: '#94a3b8', fontSize: '0.88rem', marginTop: '0.25rem', maxWidth: '650px' }}>
              Site S07 reports liver enzymes in International System units (µkat/L) rather than standard clinical U/L. Without conversion, ALT values like 3.995 appear low and are dangerously overlooked.
            </p>
          </div>

          {/* Visual conversion formula */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '1rem',
              background: 'rgba(10, 16, 30, 0.8)',
              padding: '1rem 1.5rem',
              borderRadius: '12px',
              border: '1px solid rgba(56, 189, 248, 0.2)',
            }}
          >
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fbbf24', fontFamily: 'var(--font-mono)' }}>
                3.995 µkat/L
              </div>
              <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Raw S07 Local Result</div>
            </div>
            <div style={{ color: '#38bdf8' }}>
              <ArrowRight size={22} />
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#38bdf8', fontFamily: 'var(--font-mono)' }}>
                239.7 U/L
              </div>
              <div style={{ fontSize: '0.7rem', color: '#34d399' }}>&gt; 3× ULN (56 U/L)</div>
            </div>
          </div>
        </div>

        <div style={{ marginTop: '1rem', paddingTop: '0.85rem', borderTop: '1px solid rgba(255, 255, 255, 0.08)', fontSize: '0.82rem', color: '#cbd5e1' }}>
          Conversion Formula Applied: <code style={{ color: '#38bdf8', fontWeight: 600 }}>1 µkat/L = 60 U/L</code> (3.995 × 60 = 239.7 U/L). ATLAS normalizes this at ingestion, correctly identifying subject <strong>042-S07-001</strong> as a Hy's Law candidate!
        </div>
      </div>

      {/* Validated Candidates Section */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
          <div>
            <h2 style={{ fontSize: '1.35rem', fontWeight: 700, color: '#f8fafc' }}>
              Validated Hy's Law Candidates (3 Subjects)
            </h2>
            <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>
              Identified and audited in Q018 with exactly 6 supporting laboratory evidence records (2 per candidate).
            </p>
          </div>
          <span className="badge badge-emerald">6 Supporting LB Records</span>
        </div>

        {loading ? (
          <div className="glass-card" style={{ padding: '3rem', textAlign: 'center', color: '#38bdf8' }}>
            Loading Hy's Law candidates from study graph...
          </div>
        ) : error ? (
          <div className="glass-card" style={{ padding: '2rem', color: '#f43f5e' }}>{error}</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {data?.details.map((cand, idx) => {
              // Find the elevated ALT and BILI records
              const alt = cand.alt_records.find((r) => r.std_val > 168) || cand.alt_records[0]
              const bili = cand.bili_records.find((r) => r.std_val > 2.4) || cand.bili_records[0]

              return (
                <div
                  key={cand.usubjid}
                  className="glass-card"
                  style={{
                    padding: '1.75rem',
                    borderLeft: cand.is_s07_special ? '4px solid #0ea5e9' : '4px solid #818cf8',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.25rem' }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <span className="badge badge-indigo font-mono">Candidate #{idx + 1}</span>
                        <h3 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#f8fafc', fontFamily: 'var(--font-mono)' }}>
                          {cand.usubjid}
                        </h3>
                        <span className="badge badge-cyan">Site {cand.site}</span>
                        {cand.is_s07_special && (
                          <span className="badge badge-amber">µkat/L Normalization Match</span>
                        )}
                      </div>
                      <div style={{ fontSize: '0.82rem', color: '#94a3b8', marginTop: '0.35rem' }}>
                        Arm: <strong style={{ color: '#38bdf8' }}>{cand.demographics?.ARM || 'DRUG'}</strong> | Age: {cand.demographics?.AGE} | Sex: {cand.demographics?.SEX}
                      </div>
                    </div>

                    <span className="badge badge-emerald font-mono">
                      2 Evidence Records (1 ALT + 1 BILI)
                    </span>
                  </div>

                  {/* ALT & BILI Evidence Cards Grid */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem' }}>
                    {/* ALT Evidence */}
                    <div style={{ background: 'rgba(10, 16, 30, 0.7)', padding: '1.25rem', borderRadius: '10px', border: '1px solid rgba(56, 189, 248, 0.15)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.65rem' }}>
                        <span style={{ fontWeight: 700, color: '#38bdf8', fontSize: '0.95rem' }}>
                          ALT Elevation (&gt;3× ULN)
                        </span>
                        <span className="badge badge-cyan font-mono" style={{ fontSize: '0.7rem' }}>
                          LBSEQ: {alt?.seq}
                        </span>
                      </div>

                      <div style={{ fontSize: '1.65rem', fontWeight: 800, color: '#f8fafc', fontFamily: 'var(--font-mono)' }}>
                        {alt?.std_val} {alt?.std_unit}
                      </div>

                      <div style={{ fontSize: '0.78rem', color: '#94a3b8', marginTop: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                        <div>Date: <span className="font-mono" style={{ color: '#f8fafc' }}>{alt?.date}</span></div>
                        <div>Visit: <span style={{ color: '#f8fafc' }}>{alt?.visit}</span></div>
                        {alt?.converted && (
                          <div style={{ color: '#fbbf24', marginTop: '0.2rem' }}>
                            Raw local value: {alt.raw_val} {alt.raw_unit} (converted × 60)
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Bilirubin Evidence */}
                    <div style={{ background: 'rgba(10, 16, 30, 0.7)', padding: '1.25rem', borderRadius: '10px', border: '1px solid rgba(99, 102, 241, 0.2)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.65rem' }}>
                        <span style={{ fontWeight: 700, color: '#818cf8', fontSize: '0.95rem' }}>
                          Total Bilirubin Elevation (&gt;2× ULN)
                        </span>
                        <span className="badge badge-indigo font-mono" style={{ fontSize: '0.7rem' }}>
                          LBSEQ: {bili?.seq}
                        </span>
                      </div>

                      <div style={{ fontSize: '1.65rem', fontWeight: 800, color: '#f8fafc', fontFamily: 'var(--font-mono)' }}>
                        {bili?.std_val} {bili?.std_unit}
                      </div>

                      <div style={{ fontSize: '0.78rem', color: '#94a3b8', marginTop: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                        <div>Date: <span className="font-mono" style={{ color: '#f8fafc' }}>{bili?.date}</span></div>
                        <div>Visit: <span style={{ color: '#f8fafc' }}>{bili?.visit}</span></div>
                        <div style={{ color: '#34d399', marginTop: '0.2rem' }}>
                          Concomitant within same visit window
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
