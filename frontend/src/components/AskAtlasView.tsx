import React, { useState, useRef, useEffect } from 'react'
import {
  Sparkles,
  Send,
  Bot,
  User,
  FileCheck2,
  AlertCircle,
  CheckCircle2,
  RotateCcw,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import { askAtlas } from '../api'
import type { AtlasAnswer, RecordRef } from '../types'

interface ChatMessage {
  id: string
  sender: 'user' | 'atlas'
  text: string
  timestamp: string
  answerData?: AtlasAnswer
  error?: string
}

export const AskAtlasView: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputQuery, setInputQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [evidenceLimits, setEvidenceLimits] = useState<Record<string, number>>({})
  const chatEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const suggestedQuestions = [
    'How many subjects are in the study?',
    'Tell me about 042-S07-001',
    "Which patients triggered Hy's Law?",
    'Were there any dosing errors?',
    'What changed between protocol v1 and v2?',
    'Who withdrew from the study?',
    'What lab results does 042-S07-001 have?',
    'Did 042-S07-001 have any adverse events?',
  ]

  // Auto-scroll to bottom on new message or loading state change
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const handleSend = async (queryText?: string) => {
    const textToSend = (queryText || inputQuery).trim()
    if (!textToSend || loading) return

    const userMsgId = `user-${Date.now()}`
    const atlasMsgId = `atlas-${Date.now() + 1}`
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

    const userMsg: ChatMessage = {
      id: userMsgId,
      sender: 'user',
      text: textToSend,
      timestamp: timeStr,
    }

    setMessages((prev) => [...prev, userMsg])
    setInputQuery('')
    setLoading(true)

    try {
      const res = await askAtlas(textToSend)
      const atlasMsg: ChatMessage = {
        id: atlasMsgId,
        sender: 'atlas',
        text: res.text,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        answerData: res,
      }
      setMessages((prev) => [...prev, atlasMsg])
      setEvidenceLimits((prev) => ({ ...prev, [atlasMsgId]: 8 }))
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: atlasMsgId,
        sender: 'atlas',
        text: 'I encountered an error connecting to the ATLAS engine.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        error: err.message || 'ATLAS service is temporarily unreachable.',
      }
      setMessages((prev) => [...prev, errorMsg])
    } finally {
      setLoading(false)
      // Return focus to input
      setTimeout(() => textareaRef.current?.focus(), 100)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleResetChat = () => {
    setMessages([])
    setEvidenceLimits({})
    setInputQuery('')
    textareaRef.current?.focus()
  }

  const toggleEvidenceLimit = (msgId: string, currentLimit: number, totalEvidence: number) => {
    setEvidenceLimits((prev) => ({
      ...prev,
      [msgId]: currentLimit >= totalEvidence ? 8 : currentLimit + 16,
    }))
  }

  return (
    <div style={{ maxWidth: '1100px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '1.5rem', minHeight: 'calc(100vh - 120px)' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.35rem' }}>
            <span className="badge badge-cyan">Deterministic NLU Engine</span>
            <span className="badge badge-emerald">100% Grounded Evidence</span>
          </div>
          <h1 style={{ fontSize: '2.25rem', fontWeight: 800, color: '#f8fafc', marginBottom: '0.3rem' }}>
            Ask ATLAS
          </h1>
          <p style={{ color: '#94a3b8', fontSize: '1.05rem' }}>
            Ask natural-language questions about the clinical trial. ATLAS deterministically extracts clinical entities, queries the StudyGraph, and provides grounded evidence.
          </p>
        </div>

        {messages.length > 0 && (
          <button
            onClick={handleResetChat}
            className="btn-secondary"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', padding: '0.6rem 1.1rem', fontSize: '0.85rem' }}
          >
            <RotateCcw size={15} />
            Reset Chat
          </button>
        )}
      </div>

      {/* Main Conversational Box */}
      <div
        className="glass-card"
        style={{
          display: 'flex',
          flexDirection: 'column',
          flex: 1,
          minHeight: '520px',
          background: 'rgba(10, 16, 30, 0.85)',
          border: '1px solid rgba(56, 189, 248, 0.2)',
          borderRadius: '16px',
          overflow: 'hidden',
        }}
      >
        {/* Chat Messages Stream */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '1.75rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '1.5rem',
          }}
        >
          {messages.length === 0 ? (
            /* Empty State / Suggested Questions */
            <div
              style={{
                margin: 'auto 0',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                textAlign: 'center',
                padding: '2.5rem 1rem',
                gap: '1.5rem',
              }}
            >
              <div
                style={{
                  width: '64px',
                  height: '64px',
                  borderRadius: '18px',
                  background: 'linear-gradient(135deg, rgba(14, 165, 233, 0.2) 0%, rgba(99, 102, 241, 0.2) 100%)',
                  border: '1px solid rgba(56, 189, 248, 0.4)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: '0 0 25px rgba(14, 165, 233, 0.25)',
                }}
              >
                <Bot size={32} color="#38bdf8" />
              </div>

              <div>
                <h3 style={{ fontSize: '1.35rem', fontWeight: 700, color: '#f8fafc', marginBottom: '0.35rem' }}>
                  Ask anything about the clinical study
                </h3>
                <p style={{ color: '#94a3b8', fontSize: '0.92rem', maxWidth: '560px', margin: '0 auto' }}>
                  ATLAS understands natural questions across subjects, visits, laboratory results, adverse events, medications, dosing deviations, Hy's Law findings, and protocol rules.
                </p>
              </div>

              {/* Suggested Questions Grid */}
              <div style={{ width: '100%', maxWidth: '820px' }}>
                <div style={{ fontSize: '0.8rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.75rem' }}>
                  Suggested Questions
                </div>
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
                    gap: '0.75rem',
                  }}
                >
                  {suggestedQuestions.map((sq) => (
                    <button
                      key={sq}
                      type="button"
                      onClick={() => handleSend(sq)}
                      className="glass-card glass-card-interactive"
                      style={{
                        padding: '0.9rem 1.1rem',
                        textAlign: 'left',
                        background: 'rgba(15, 23, 42, 0.75)',
                        border: '1px solid rgba(56, 189, 248, 0.15)',
                        color: '#f8fafc',
                        fontSize: '0.88rem',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        gap: '0.5rem',
                      }}
                    >
                      <span>{sq}</span>
                      <Sparkles size={15} color="#38bdf8" style={{ flexShrink: 0, opacity: 0.8 }} />
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            /* Chat History */
            messages.map((msg) => {
              const isUser = msg.sender === 'user'
              const ans = msg.answerData
              const currentEvidenceLimit = evidenceLimits[msg.id] || 8
              const totalEvidence = ans?.evidence?.length || 0

              return (
                <div
                  key={msg.id}
                  style={{
                    display: 'flex',
                    flexDirection: isUser ? 'row-reverse' : 'row',
                    gap: '0.85rem',
                    alignItems: 'flex-start',
                    maxWidth: '100%',
                  }}
                >
                  {/* Avatar */}
                  <div
                    style={{
                      width: '38px',
                      height: '38px',
                      borderRadius: '10px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                      background: isUser
                        ? 'linear-gradient(135deg, #0284c7 0%, #2563eb 100%)'
                        : 'linear-gradient(135deg, rgba(14, 165, 233, 0.25) 0%, rgba(99, 102, 241, 0.25) 100%)',
                      border: isUser ? 'none' : '1px solid rgba(56, 189, 248, 0.35)',
                      boxShadow: isUser ? '0 4px 12px rgba(2, 132, 199, 0.3)' : '0 4px 12px rgba(14, 165, 233, 0.15)',
                    }}
                  >
                    {isUser ? <User size={18} color="#ffffff" /> : <Bot size={20} color="#38bdf8" />}
                  </div>

                  {/* Message Bubble Content */}
                  <div
                    style={{
                      maxWidth: isUser ? '75%' : '88%',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '0.6rem',
                    }}
                  >
                    {/* Header: Sender & Timestamp */}
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        fontSize: '0.75rem',
                        color: '#64748b',
                        justifyContent: isUser ? 'flex-end' : 'flex-start',
                        padding: '0 0.25rem',
                      }}
                    >
                      <span style={{ fontWeight: 600, color: isUser ? '#93c5fd' : '#38bdf8' }}>
                        {isUser ? 'You' : 'ATLAS'}
                      </span>
                      <span>•</span>
                      <span>{msg.timestamp}</span>
                    </div>

                    {/* User Text Bubble */}
                    {isUser && (
                      <div
                        style={{
                          padding: '0.9rem 1.25rem',
                          borderRadius: '14px',
                          borderTopRightRadius: '3px',
                          background: 'linear-gradient(135deg, #0369a1 0%, #1d4ed8 100%)',
                          color: '#ffffff',
                          fontSize: '1rem',
                          lineHeight: 1.5,
                          boxShadow: '0 4px 14px rgba(0, 0, 0, 0.3)',
                          whiteSpace: 'pre-wrap',
                          wordBreak: 'break-word',
                        }}
                      >
                        {msg.text}
                      </div>
                    )}

                    {/* Error State */}
                    {msg.error && (
                      <div
                        className="glass-card"
                        style={{
                          padding: '1.25rem',
                          borderLeft: '4px solid #f43f5e',
                          background: 'rgba(244, 63, 94, 0.08)',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#f8fafc', fontWeight: 700 }}>
                          <AlertCircle size={17} color="#f43f5e" />
                          Evaluation Notice
                        </div>
                        <div style={{ color: '#fda4af', fontSize: '0.88rem', marginTop: '0.35rem' }}>
                          {msg.error}
                        </div>
                      </div>
                    )}

                    {/* ATLAS Structured Response */}
                    {!isUser && !msg.error && (
                      <div
                        style={{
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '1rem',
                          width: '100%',
                        }}
                      >
                        {/* Main Response Box */}
                        <div
                          className="glass-card"
                          style={{
                            padding: '1.5rem',
                            borderLeft: '4px solid #0ea5e9',
                            background: 'linear-gradient(135deg, rgba(14, 165, 233, 0.07) 0%, rgba(15, 23, 42, 0.85) 100%)',
                          }}
                        >
                          {/* Answer Value Highlight if available */}
                          {ans && ans.answer !== null && ans.answer !== undefined && (
                            <div style={{ marginBottom: '1rem', paddingBottom: '1rem', borderBottom: '1px solid rgba(255, 255, 255, 0.07)' }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.5rem' }}>
                                <span className="badge badge-cyan">Clinical Answer</span>
                                <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
                                  <span className="badge badge-emerald" style={{ fontSize: '0.72rem' }}>
                                    Confidence: {Math.round(ans.confidence * 100)}%
                                  </span>
                                  <span className="badge badge-indigo" style={{ fontSize: '0.72rem' }}>
                                    {ans.steps_used} step(s)
                                  </span>
                                </div>
                              </div>

                              {/* Array of Subjects / Entities */}
                              {Array.isArray(ans.answer) ? (
                                <div>
                                  {ans.answer.length === 0 ? (
                                    <div style={{ color: '#94a3b8', fontStyle: 'italic', fontSize: '0.95rem' }}>
                                      [None / Empty set]
                                    </div>
                                  ) : (
                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginTop: '0.35rem' }}>
                                      {ans.answer.map((item: any, i: number) => {
                                        const strItem = typeof item === 'object' ? JSON.stringify(item) : String(item)
                                        const isSubjid = /^042-S\d{2}-\d{3}$/.test(strItem)
                                        return (
                                          <span
                                            key={i}
                                            className={isSubjid ? 'badge badge-cyan' : 'badge badge-indigo'}
                                            style={{
                                              fontFamily: 'var(--font-mono)',
                                              fontSize: '0.85rem',
                                              padding: '0.3rem 0.65rem',
                                            }}
                                          >
                                            {strItem}
                                          </span>
                                        )
                                      })}
                                    </div>
                                  )}
                                </div>
                              ) : typeof ans.answer === 'object' ? (
                                /* Structured Object */
                                <div
                                  style={{
                                    background: 'rgba(10, 16, 30, 0.6)',
                                    padding: '0.75rem 1rem',
                                    borderRadius: '8px',
                                    border: '1px solid rgba(255, 255, 255, 0.06)',
                                    fontSize: '0.85rem',
                                    fontFamily: 'var(--font-mono)',
                                    color: '#e2e8f0',
                                    overflowX: 'auto',
                                  }}
                                >
                                  <pre style={{ margin: 0 }}>{JSON.stringify(ans.answer, null, 2)}</pre>
                                </div>
                              ) : (
                                /* Scalar Value (Number or String) */
                                <div
                                  style={{
                                    fontSize: '2rem',
                                    fontWeight: 800,
                                    color: '#f8fafc',
                                    fontFamily: 'var(--font-mono)',
                                  }}
                                >
                                  {String(ans.answer)}
                                </div>
                              )}
                            </div>
                          )}

                          {/* Explanation Paragraph */}
                          <div style={{ color: '#f8fafc', fontSize: '1rem', lineHeight: 1.6 }}>
                            {msg.text}
                          </div>
                        </div>

                        {/* Grounded Evidence Section */}
                        {ans && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', fontSize: '0.9rem', fontWeight: 600, color: '#94a3b8' }}>
                                <FileCheck2 size={16} color="#38bdf8" />
                                <span>Grounded Evidence ({totalEvidence} RecordRef{totalEvidence === 1 ? '' : 's'})</span>
                              </div>

                              {totalEvidence > 0 && (
                                <span className="badge badge-cyan font-mono" style={{ fontSize: '0.7rem' }}>
                                  {totalEvidence} Cited
                                </span>
                              )}
                            </div>

                            {totalEvidence === 0 ? (
                              <div
                                className="glass-card"
                                style={{
                                  padding: '1.1rem',
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '0.75rem',
                                  background: 'rgba(15, 23, 42, 0.5)',
                                  border: '1px solid rgba(255, 255, 255, 0.05)',
                                }}
                              >
                                <CheckCircle2 size={20} color="#34d399" />
                                <div style={{ fontSize: '0.85rem', color: '#94a3b8' }}>
                                  0 supporting records cited. ATLAS does not fabricate evidence when no matching records exist.
                                </div>
                              </div>
                            ) : (
                              /* Evidence Cards Grid */
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                <div
                                  style={{
                                    display: 'grid',
                                    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
                                    gap: '0.85rem',
                                  }}
                                >
                                  {ans.evidence.slice(0, currentEvidenceLimit).map((ref: RecordRef, idx: number) => {
                                    const details = ref.details || {}
                                    return (
                                      <div
                                        key={idx}
                                        className="glass-card"
                                        style={{
                                          padding: '1rem',
                                          display: 'flex',
                                          flexDirection: 'column',
                                          gap: '0.6rem',
                                          background: 'rgba(15, 23, 42, 0.65)',
                                          border: '1px solid rgba(56, 189, 248, 0.15)',
                                        }}
                                      >
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                          <span className="badge badge-cyan font-mono" style={{ fontSize: '0.7rem' }}>
                                            #{idx + 1}
                                          </span>
                                          <span className="badge badge-indigo font-mono" style={{ fontSize: '0.7rem' }}>
                                            Domain: {ref.domain}
                                          </span>
                                        </div>

                                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', fontSize: '0.82rem' }}>
                                          {ref.usubjid && (
                                            <div>
                                              <div style={{ color: '#64748b', fontSize: '0.68rem', textTransform: 'uppercase' }}>Subject</div>
                                              <div style={{ fontWeight: 600, color: '#f8fafc', fontFamily: 'var(--font-mono)' }}>
                                                {ref.usubjid}
                                              </div>
                                            </div>
                                          )}

                                          <div>
                                            <div style={{ color: '#64748b', fontSize: '0.68rem', textTransform: 'uppercase' }}>Sequence</div>
                                            <div style={{ fontWeight: 600, color: '#38bdf8', fontFamily: 'var(--font-mono)' }}>
                                              {ref.seq !== undefined && ref.seq !== null ? ref.seq : 'N/A (DM)'}
                                            </div>
                                          </div>

                                          {details.date && (
                                            <div>
                                              <div style={{ color: '#64748b', fontSize: '0.68rem', textTransform: 'uppercase' }}>Date</div>
                                              <div style={{ color: '#cbd5e1', fontFamily: 'var(--font-mono)' }}>
                                                {details.date}
                                              </div>
                                            </div>
                                          )}

                                          {details.test && (
                                            <div>
                                              <div style={{ color: '#64748b', fontSize: '0.68rem', textTransform: 'uppercase' }}>Test</div>
                                              <div style={{ fontWeight: 600, color: '#f8fafc' }}>
                                                {details.test}
                                              </div>
                                            </div>
                                          )}

                                          {(details.value !== undefined || details.raw_value !== undefined) && (
                                            <div>
                                              <div style={{ color: '#64748b', fontSize: '0.68rem', textTransform: 'uppercase' }}>Value</div>
                                              <div style={{ fontWeight: 600, color: '#38bdf8' }}>
                                                {details.value !== undefined && details.value !== null
                                                  ? details.value
                                                  : details.raw_value}
                                                {details.unit ? ` ${details.unit}` : ''}
                                              </div>
                                            </div>
                                          )}

                                          {details.converted && (
                                            <div>
                                              <span className="badge badge-amber" style={{ fontSize: '0.65rem' }}>
                                                60x µkat/L converted
                                              </span>
                                            </div>
                                          )}

                                          {details.term && (
                                            <div style={{ gridColumn: 'span 2' }}>
                                              <div style={{ color: '#64748b', fontSize: '0.68rem', textTransform: 'uppercase' }}>Term / Finding</div>
                                              <div style={{ color: '#f8fafc', fontWeight: 600 }}>{details.term}</div>
                                            </div>
                                          )}

                                          {details.treatment && (
                                            <div style={{ gridColumn: 'span 2' }}>
                                              <div style={{ color: '#64748b', fontSize: '0.68rem', textTransform: 'uppercase' }}>Treatment</div>
                                              <div style={{ color: '#f8fafc', fontWeight: 600 }}>{details.treatment}</div>
                                            </div>
                                          )}

                                          {ref.document && (
                                            <div style={{ gridColumn: 'span 2' }}>
                                              <div style={{ color: '#64748b', fontSize: '0.68rem', textTransform: 'uppercase' }}>Document Citation</div>
                                              <div style={{ color: '#38bdf8', fontWeight: 600 }}>
                                                {ref.document} ({ref.section || 'amendment'})
                                              </div>
                                            </div>
                                          )}
                                        </div>
                                      </div>
                                    )
                                  })}
                                </div>

                                {/* Pagination / Expand Toggle */}
                                {totalEvidence > 8 && (
                                  <div style={{ textAlign: 'center', marginTop: '0.5rem' }}>
                                    <button
                                      type="button"
                                      className="btn-secondary"
                                      onClick={() => toggleEvidenceLimit(msg.id, currentEvidenceLimit, totalEvidence)}
                                      style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', padding: '0.45rem 1rem' }}
                                    >
                                      {currentEvidenceLimit >= totalEvidence ? (
                                        <>
                                          <ChevronUp size={14} />
                                          Collapse Citations
                                        </>
                                      ) : (
                                        <>
                                          <ChevronDown size={14} />
                                          Show More Citations ({totalEvidence - currentEvidenceLimit} remaining)
                                        </>
                                      )}
                                    </button>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )
            })
          )}

          {/* Loading Animation State */}
          {loading && (
            <div
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '0.85rem',
                maxWidth: '80%',
              }}
            >
              <div
                style={{
                  width: '38px',
                  height: '38px',
                  borderRadius: '10px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: 'linear-gradient(135deg, rgba(14, 165, 233, 0.25) 0%, rgba(99, 102, 241, 0.25) 100%)',
                  border: '1px solid rgba(56, 189, 248, 0.35)',
                  boxShadow: '0 4px 12px rgba(14, 165, 233, 0.15)',
                }}
              >
                <Bot size={20} color="#38bdf8" />
              </div>

              <div
                className="glass-card pulse-glow"
                style={{
                  padding: '1.1rem 1.5rem',
                  background: 'rgba(14, 165, 233, 0.06)',
                  border: '1px solid rgba(56, 189, 248, 0.3)',
                  borderRadius: '14px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.85rem',
                }}
              >
                <div
                  style={{
                    width: '16px',
                    height: '16px',
                    borderRadius: '50%',
                    border: '2px solid #38bdf8',
                    borderTopColor: 'transparent',
                    animation: 'spin 1s linear infinite',
                  }}
                />
                <span style={{ color: '#38bdf8', fontWeight: 600, fontSize: '0.95rem' }}>
                  ATLAS is analyzing the study data...
                </span>
              </div>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>

        {/* Input Bar Area */}
        <div
          style={{
            padding: '1.25rem 1.75rem',
            background: 'rgba(8, 12, 22, 0.95)',
            borderTop: '1px solid rgba(56, 189, 248, 0.15)',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.75rem',
          }}
        >
          {/* Quick chips if chat has history */}
          {messages.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', overflowX: 'auto', paddingBottom: '0.2rem' }}>
              <span style={{ fontSize: '0.72rem', color: '#64748b', flexShrink: 0 }}>Try:</span>
              {suggestedQuestions.slice(0, 4).map((sq) => (
                <button
                  key={sq}
                  type="button"
                  onClick={() => handleSend(sq)}
                  className="badge badge-indigo"
                  style={{ cursor: 'pointer', whiteSpace: 'nowrap', fontSize: '0.72rem' }}
                >
                  {sq}
                </button>
              ))}
            </div>
          )}

          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-end' }}>
            <textarea
              ref={textareaRef}
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything about the study... (Press Enter to send, Shift+Enter for new line)"
              rows={1}
              style={{
                flex: 1,
                resize: 'none',
                minHeight: '50px',
                maxHeight: '140px',
                padding: '0.85rem 1.1rem',
                fontSize: '0.95rem',
                borderRadius: '12px',
                border: '1px solid rgba(56, 189, 248, 0.25)',
                background: 'rgba(15, 23, 42, 0.85)',
                color: '#f8fafc',
                fontFamily: 'inherit',
                outline: 'none',
                lineHeight: 1.4,
              }}
            />

            <button
              type="button"
              onClick={() => handleSend()}
              disabled={loading || !inputQuery.trim()}
              className="btn-primary"
              style={{
                padding: '0.85rem 1.5rem',
                height: '50px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.5rem',
                opacity: loading || !inputQuery.trim() ? 0.6 : 1,
                cursor: loading || !inputQuery.trim() ? 'not-allowed' : 'pointer',
              }}
            >
              <Send size={16} />
              <span>Send</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
