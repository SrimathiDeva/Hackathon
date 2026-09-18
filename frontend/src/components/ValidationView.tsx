import React, { useState, useEffect } from 'react'
import {
  CheckCircle2,
  ShieldCheck,
  Zap,
  Clock,
  Layers,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import { fetchPublicQuestions } from '../api'
import type { PublicQuestionItem } from '../types'

export const ValidationView: React.FC = () => {
  const [questions, setQuestions] = useState<PublicQuestionItem[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<string | null>('Q018')

  useEffect(() => {
    fetchPublicQuestions()
      .then((res) => {
        setQuestions(res)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  const toggleExpand = (id: string) => {
    setExpandedId((prev) => (prev === id ? null : id))
  }

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '2.5rem' }}>
      {/* Header */}
      <div>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
          <span className="badge badge-emerald">Audit & Benchmark Verified</span>
        </div>
        <h1 style={{ fontSize: '2.25rem', fontWeight: 800, color: '#f8fafc', marginBottom: '0.4rem' }}>
          ATLAS Solution Validation
        </h1>
        <p style={{ color: '#94a3b8', fontSize: '1.05rem', maxWidth: '820px' }}>
          Verified against the public benchmark questions, clinical datasets, and schema compliance criteria via <code>audit.py</code> and <code>main.py</code>.
        </p>
      </div>

      {/* Validation Metric Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: '1.25rem',
        }}
      >
        {/* Public Benchmark */}
        <div className="glass-card" style={{ padding: '1.5rem', borderLeft: '4px solid #10b981' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.85rem', color: '#94a3b8', fontWeight: 600 }}>Public Benchmark</span>
            <CheckCircle2 size={20} color="#34d399" />
          </div>
          <div style={{ fontSize: '2.25rem', fontWeight: 800, color: '#f8fafc' }}>
            10 / 10
          </div>
          <div style={{ fontSize: '0.82rem', color: '#34d399', marginTop: '0.25rem' }}>
            Questions executed successfully
          </div>
        </div>

        {/* Evidence Audit */}
        <div className="glass-card" style={{ padding: '1.5rem', borderLeft: '4px solid #10b981' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.85rem', color: '#94a3b8', fontWeight: 600 }}>Evidence Audit</span>
            <ShieldCheck size={20} color="#34d399" />
          </div>
          <div style={{ fontSize: '2.25rem', fontWeight: 800, color: '#34d399' }}>
            PASS
          </div>
          <div style={{ fontSize: '0.82rem', color: '#94a3b8', marginTop: '0.25rem' }}>
            All evidence references verified in CSVs
          </div>
        </div>

        {/* Performance */}
        <div className="glass-card" style={{ padding: '1.5rem', borderLeft: '4px solid #0ea5e9' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.85rem', color: '#94a3b8', fontWeight: 600 }}>Performance</span>
            <Zap size={20} color="#38bdf8" />
          </div>
          <div style={{ fontSize: '2.25rem', fontWeight: 800, color: '#38bdf8' }}>
            ~219 ms
          </div>
          <div style={{ fontSize: '0.82rem', color: '#94a3b8', marginTop: '0.25rem' }}>
            In-memory graph build time
          </div>
        </div>

        {/* Q018 Hy's Law */}
        <div className="glass-card" style={{ padding: '1.5rem', borderLeft: '4px solid #818cf8' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.85rem', color: '#94a3b8', fontWeight: 600 }}>Q018 (Hy's Law)</span>
            <span className="badge badge-indigo font-mono">PASS</span>
          </div>
          <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#f8fafc' }}>
            3 Candidates
          </div>
          <div style={{ fontSize: '0.82rem', color: '#94a3b8', marginTop: '0.25rem' }}>
            Supported by exactly 6 LB records
          </div>
        </div>

        {/* Q031 Trap */}
        <div className="glass-card" style={{ padding: '1.5rem', borderLeft: '4px solid #fbbf24' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.85rem', color: '#94a3b8', fontWeight: 600 }}>Q031 (Dosing Trap)</span>
            <span className="badge badge-amber font-mono">PASS</span>
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 700, color: '#f8fafc', fontFamily: 'var(--font-mono)' }}>
            []
          </div>
          <div style={{ fontSize: '0.82rem', color: '#94a3b8', marginTop: '0.25rem' }}>
            No dosing error at S01 (honest refusal)
          </div>
        </div>

        {/* Dataset */}
        <div className="glass-card" style={{ padding: '1.5rem', borderLeft: '4px solid #0ea5e9' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.85rem', color: '#94a3b8', fontWeight: 600 }}>Dataset Ingestion</span>
            <Layers size={20} color="#38bdf8" />
          </div>
          <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#f8fafc' }}>
            12 Cuts / 200 Corrs
          </div>
          <div style={{ fontSize: '0.82rem', color: '#94a3b8', marginTop: '0.25rem' }}>
            241 enrollments / 26,925 records
          </div>
        </div>
      </div>

      {/* Explicit Notice on Hidden 40-Question Evaluator */}
      <div
        className="glass-card"
        style={{
          padding: '1.5rem',
          borderLeft: '4px solid #64748b',
          background: 'rgba(15, 23, 42, 0.7)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
          <Clock size={18} color="#94a3b8" />
          <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#f8fafc' }}>
            Evaluation Status Notice
          </h3>
        </div>
        <div style={{ fontSize: '0.92rem', color: '#cbd5e1' }}>
          <strong>Hidden 40-question evaluator:</strong> <span style={{ color: '#fbbf24' }}>Not yet run</span>.
        </div>
        <p style={{ fontSize: '0.82rem', color: '#94a3b8', marginTop: '0.35rem' }}>
          Per hackathon guidelines, all metrics shown are from the verified public benchmark suite (<code>stage1_public.json</code>) and the automated evidence audit (<code>audit.py</code>).
        </p>
      </div>

      {/* Public Benchmark Questions Accordion */}
      <div className="glass-card" style={{ padding: '2rem' }}>
        <h2 style={{ fontSize: '1.3rem', fontWeight: 700, color: '#f8fafc', marginBottom: '1.25rem' }}>
          Public Benchmark Execution (10 Questions)
        </h2>

        {loading ? (
          <div style={{ color: '#38bdf8' }}>Loading benchmark questions...</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {questions.map((q) => {
              const isExpanded = expandedId === q.question_id
              return (
                <div
                  key={q.question_id}
                  style={{
                    border: '1px solid rgba(56, 189, 248, 0.15)',
                    borderRadius: '10px',
                    background: 'rgba(10, 16, 30, 0.6)',
                    overflow: 'hidden',
                  }}
                >
                  <button
                    onClick={() => toggleExpand(q.question_id)}
                    style={{
                      width: '100%',
                      padding: '1rem 1.25rem',
                      background: 'transparent',
                      border: 'none',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      cursor: 'pointer',
                      textAlign: 'left',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
                      <span className="badge badge-cyan font-mono">{q.question_id}</span>
                      <span className="badge badge-indigo font-mono">{q.kind.toUpperCase()}</span>
                      <span style={{ fontWeight: 600, color: '#f8fafc', fontSize: '0.95rem' }}>
                        {q.text}
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                      <span className="badge badge-emerald">
                        Ans: {typeof q.answer === 'object' ? JSON.stringify(q.answer) : String(q.answer)}
                      </span>
                      {isExpanded ? <ChevronUp size={18} color="#94a3b8" /> : <ChevronDown size={18} color="#94a3b8" />}
                    </div>
                  </button>

                  {isExpanded && (
                    <div style={{ padding: '1rem 1.25rem', borderTop: '1px solid rgba(255, 255, 255, 0.06)', background: 'rgba(15, 23, 42, 0.8)' }}>
                      <div style={{ fontSize: '0.82rem', color: '#94a3b8', marginBottom: '0.5rem' }}>
                        <strong>Explanation:</strong> {q.explanation}
                      </div>
                      <div style={{ display: 'flex', gap: '1rem', fontSize: '0.8rem', color: '#64748b' }}>
                        <span>Confidence: <strong style={{ color: '#34d399' }}>{Math.round(q.confidence * 100)}%</strong></span>
                        <span>Evidence Records: <strong style={{ color: '#38bdf8' }}>{q.evidence_count}</strong></span>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
