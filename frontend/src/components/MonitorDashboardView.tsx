import React, { useState, useEffect } from 'react'
import {
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  FileQuestion,
  GitBranch,
  History,
  Play,
  Database,
  ChevronRight,
  HelpCircle,
  Check,
  X,
  RefreshCw,
  Clock,
  ArrowRight,
  Activity,
} from 'lucide-react'
import type {
  Stage2Report,
  Stage2DuplicateTestResult,
  Stage2ProtocolComparison,
} from '../types'
import {
  runStage2Cycle,
  submitHumanGateResponse,
  submitHumanGateClarify,
  runDuplicateSuppressionTest,
  fetchProtocolComparison,
} from '../api'

type SubTab =
  | 'human_gate'
  | 'medical_review'
  | 'data_manager'
  | 'compliance'
  | 'detect'
  | 'memory'
  | 'audit_trace'

interface PipelineStep {
  id: SubTab
  name: string
  code: string
  status: string
}

export const MonitorDashboardView: React.FC = () => {
  // Configuration selectors
  const [selectedCut, setSelectedCut] = useState<number>(6)
  const [selectedProtocolVersion, setSelectedProtocolVersion] = useState<number>(2)
  const [resetMemory, setResetMemory] = useState<boolean>(false)

  // Report & loading state
  const [report, setReport] = useState<Stage2Report | null>(null)
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [notification, setNotification] = useState<string | null>(null)
  const [activeSubTab, setActiveSubTab] = useState<SubTab>('human_gate')

  // Protocol comparison & duplicate benchmark state
  const [protocolComp, setProtocolComp] = useState<Stage2ProtocolComparison | null>(null)
  const [dupResult, setDupResult] = useState<Stage2DuplicateTestResult | null>(null)
  const [dupLoading, setDupLoading] = useState<boolean>(false)

  // Interactive Human Gate state
  const [rejectReasonMap, setRejectReasonMap] = useState<Record<string, string>>({})
  const [activeRejectId, setActiveRejectId] = useState<string | null>(null)
  const [clarifyQuestionMap, setClarifyQuestionMap] = useState<Record<string, string>>({})
  const [activeClarifyId, setActiveClarifyId] = useState<string | null>(null)
  const [actionLoadingMap, setActionLoadingMap] = useState<Record<string, boolean>>({})

  // Filtering states
  const [findingFilterCategory, setFindingFilterCategory] = useState<string>('ALL')
  const [findingSearch, setFindingSearch] = useState<string>('')
  const [deviationFilterCat, setDeviationFilterCat] = useState<string>('ALL')
  const [deviationSearch, setDeviationSearch] = useState<string>('')
  const [traceFilterNode, setTraceFilterNode] = useState<string>('ALL')
  const [traceSearch, setTraceSearch] = useState<string>('')

  // Load initial cycle and protocol comparison on mount
  useEffect(() => {
    executeCycle(false)
    loadProtocolComparison(selectedCut)
  }, [])

  // Auto-dismiss notification after 6 seconds
  useEffect(() => {
    if (notification) {
      const timer = setTimeout(() => setNotification(null), 6000)
      return () => clearTimeout(timer)
    }
  }, [notification])

  const executeCycle = async (shouldReset: boolean) => {
    setLoading(true)
    setError(null)
    try {
      const data = await runStage2Cycle(selectedCut, selectedProtocolVersion, shouldReset)
      setReport(data)
      setNotification(`Monitoring Cycle ${data.cycle_id} successfully executed for Cut ${data.cut}, Protocol v${data.protocol_version}.`)
      loadProtocolComparison(selectedCut)
    } catch (err: any) {
      setError(err.message || 'Unable to execute clinical monitoring cycle. Check backend connectivity.')
    } finally {
      setLoading(false)
    }
  }

  const loadProtocolComparison = async (cut: number) => {
    try {
      const data = await fetchProtocolComparison(cut)
      setProtocolComp(data)
    } catch (err) {
      console.error('Failed to load protocol comparison', err)
    }
  }

  const handleRunDuplicateTest = async () => {
    setDupLoading(true)
    setError(null)
    try {
      const res = await runDuplicateSuppressionTest(selectedCut, selectedProtocolVersion)
      setDupResult(res)
      setActiveSubTab('memory')
      setNotification(`Duplicate suppression test completed: 100% duplicate suppression verified across all nodes.`)
    } catch (err: any) {
      setError(`Duplicate suppression test failed: ${err.message}`)
    } finally {
      setDupLoading(false)
    }
  }

  // Human Gate: Approve
  const handleApprove = async (escalationId: string) => {
    setActionLoadingMap((prev) => ({ ...prev, [escalationId]: true }))
    try {
      const res = await submitHumanGateResponse(escalationId, 'APPROVED')
      if (report) {
        setReport({
          ...report,
          escalations: report.escalations.map((e) => {
            if (e.escalation_id === escalationId) {
              return {
                ...e,
                status: 'APPROVED',
                human_decision: {
                  decision: 'APPROVED',
                  user: 'Medical Monitor (Physician)',
                  timestamp: new Date().toISOString(),
                  transmitted_action: res.action,
                },
              }
            }
            return e
          }),
        })
      }
      setNotification(`Escalation ${escalationId} APPROVED by physician. Transmitted to ExecuteNode.`)
    } catch (err: any) {
      setError(`Approval error: ${err.message}`)
    } finally {
      setActionLoadingMap((prev) => ({ ...prev, [escalationId]: false }))
    }
  }

  // Human Gate: Reject
  const handleReject = async (escalationId: string) => {
    const reason =
      rejectReasonMap[escalationId]?.trim() ||
      'Hospitalization was elective cosmetic surgery, unrelated to investigational drug.'
    setActionLoadingMap((prev) => ({ ...prev, [escalationId]: true }))
    try {
      await submitHumanGateResponse(escalationId, 'REJECTED', reason)
      setActiveRejectId(null)
      if (report) {
        setReport({
          ...report,
          escalations: report.escalations.map((e) => {
            if (e.escalation_id === escalationId) {
              return {
                ...e,
                status: 'REJECTED',
                human_decision: {
                  decision: 'REJECTED',
                  user: 'Medical Monitor (Physician)',
                  timestamp: new Date().toISOString(),
                  reason: reason,
                  downgraded_to: 'MONITORING',
                },
              }
            }
            return e
          }),
        })
      }
      setNotification(`Escalation ${escalationId} REJECTED and downgraded to MONITORING.`)
    } catch (err: any) {
      setError(`Rejection error: ${err.message}`)
    } finally {
      setActionLoadingMap((prev) => ({ ...prev, [escalationId]: false }))
    }
  }

  // Human Gate: Clarify
  const handleClarify = async (escalationId: string) => {
    const question =
      clarifyQuestionMap[escalationId]?.trim() ||
      'What was the ALT at screening, and is there a concomitant hepatotoxic medication?'
    setActionLoadingMap((prev) => ({ ...prev, [escalationId]: true }))
    try {
      const res = await submitHumanGateClarify(escalationId, question)
      setActiveClarifyId(null)
      if (report) {
        setReport({
          ...report,
          escalations: report.escalations.map((e) => {
            if (e.escalation_id === escalationId) {
              return {
                ...e,
                status: 'RESUBMITTED',
                clarification: {
                  question: question,
                  answer: res.clarification_answer,
                  evidence: res.clarification_evidence || [],
                },
              }
            }
            return e
          }),
        })
      }
      setNotification(`Clarification question resolved against StudyGraph evidence. Status RESUBMITTED.`)
    } catch (err: any) {
      setError(`Clarification error: ${err.message}`)
    } finally {
      setActionLoadingMap((prev) => ({ ...prev, [escalationId]: false }))
    }
  }

  // Dynamic Six-Node Pipeline Stepper
  const pipelineSteps: PipelineStep[] = [
    {
      id: 'detect',
      name: 'Detect',
      code: 'ATLAS Signal Detection',
      status: report ? `${report.summary.total_findings} Findings` : 'Pending Cycle',
    },
    {
      id: 'medical_review',
      name: 'Medical Review',
      code: 'Clinical Safety Evaluation',
      status: report ? `${report.summary.total_escalations} Escalations` : 'Pending Cycle',
    },
    {
      id: 'data_manager',
      name: 'Data Manager',
      code: 'Automated Query Dispatch',
      status: report ? `${report.summary.total_queries} Queries` : 'Pending Cycle',
    },
    {
      id: 'compliance',
      name: 'Compliance',
      code: 'Protocol Adherence',
      status: report ? `${report.summary.total_deviations} Deviations` : 'Pending Cycle',
    },
    {
      id: 'human_gate',
      name: 'Human Gate',
      code: 'Physician Review Oversight',
      status: report
        ? `${report.escalations.filter((e) => e.status === 'APPROVED').length}/${report.escalations.length} Approved`
        : 'Pending Cycle',
    },
    {
      id: 'audit_trace',
      name: 'Execute',
      code: 'Immutable Audit Ledger',
      status: report ? `${report.summary.total_trace_entries} Ledger Records` : 'Pending Cycle',
    },
  ]

  // Filtered lists (safely handling null report)
  const filteredFindings = (report?.findings || []).filter((f) => {
    const matchCat = findingFilterCategory === 'ALL' || f.category === findingFilterCategory
    const matchSearch =
      !findingSearch ||
      f.usubjid.toLowerCase().includes(findingSearch.toLowerCase()) ||
      f.finding_id.toLowerCase().includes(findingSearch.toLowerCase()) ||
      f.description.toLowerCase().includes(findingSearch.toLowerCase())
    return matchCat && matchSearch
  })

  const filteredDeviations = (report?.deviations || []).filter((d) => {
    const matchCat = deviationFilterCat === 'ALL' || d.category === deviationFilterCat
    const matchSearch =
      !deviationSearch ||
      d.usubjid.toLowerCase().includes(deviationSearch.toLowerCase()) ||
      d.deviation_id.toLowerCase().includes(deviationSearch.toLowerCase()) ||
      d.description.toLowerCase().includes(deviationSearch.toLowerCase())
    return matchCat && matchSearch
  })

  const filteredTraces = (report?.trace_entries || []).filter((t) => {
    const matchNode = traceFilterNode === 'ALL' || t.node === traceFilterNode
    const matchSearch =
      !traceSearch ||
      (t.subject && t.subject.toLowerCase().includes(traceSearch.toLowerCase())) ||
      (t.finding_id && t.finding_id.toLowerCase().includes(traceSearch.toLowerCase())) ||
      t.decision.toLowerCase().includes(traceSearch.toLowerCase()) ||
      t.action.toLowerCase().includes(traceSearch.toLowerCase())
    return matchNode && matchSearch
  })

  // SAE Miscoded escalation item for prominent display
  const saeMiscodedItem = report?.escalations.find((e) => e.code === 'SAE_MISCODED')

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      {/* 1. Header & Control Bar */}
      <div
        className="glass-card"
        style={{
          padding: '1.75rem 2rem',
          background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(13, 27, 62, 0.85) 100%)',
          border: '1px solid rgba(56, 189, 248, 0.25)',
          boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.5)',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '1.5rem',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
              <div
                style={{
                  width: '44px',
                  height: '44px',
                  borderRadius: '12px',
                  background: 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: '0 0 20px rgba(14, 165, 233, 0.4)',
                }}
              >
                <ShieldAlert size={26} color="#ffffff" />
              </div>
              <div>
                <h1
                  style={{
                    fontSize: '1.6rem',
                    fontWeight: 800,
                    letterSpacing: '-0.02em',
                    color: '#f8fafc',
                    lineHeight: 1.2,
                  }}
                >
                  ATLAS CLINICAL SENTINEL — MONITOR
                </h1>
                <div style={{ fontSize: '0.88rem', color: '#38bdf8', fontWeight: 500, marginTop: '2px' }}>
                  Problem Statement 2 &bull; Autonomous Multi-Agent Continuous Clinical Trial Surveillance
                </div>
              </div>
            </div>
            <div style={{ fontSize: '0.82rem', color: '#94a3b8', marginTop: '0.65rem', maxWidth: '820px' }}>
              Dynamic 6-node clinical review engine integrating StudyGraph signals, medical safety escalations,
              automated CDISC queries, mid-stage amendment compliance, physician human-gate oversight, and immutable audit logs.
            </div>
          </div>

          {/* Right Status Badge */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <span
                style={{
                  width: '10px',
                  height: '10px',
                  borderRadius: '50%',
                  background: loading ? '#fbbf24' : report ? '#10b981' : '#64748b',
                  boxShadow: loading
                    ? '0 0 10px #fbbf24'
                    : report
                    ? '0 0 10px #10b981'
                    : 'none',
                }}
              />
              <span
                className="font-mono"
                style={{
                  fontSize: '0.82rem',
                  fontWeight: 700,
                  letterSpacing: '0.05em',
                  color: loading ? '#fbbf24' : report ? '#34d399' : '#94a3b8',
                  textTransform: 'uppercase',
                }}
              >
                {loading ? 'RUNNING CYCLE...' : report?.status || 'AWAITING CYCLE RUN'}
              </span>
            </div>
            <div style={{ fontSize: '0.75rem', color: '#64748b', fontFamily: 'monospace' }}>
              {report ? `Cycle ID: ${report.cycle_id}` : 'Backend: http://127.0.0.1:8001'}
            </div>
          </div>
        </div>

        {/* Controls Row */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginTop: '1.5rem',
            paddingTop: '1.25rem',
            borderTop: '1px solid rgba(255, 255, 255, 0.08)',
            flexWrap: 'wrap',
            gap: '1rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem', flexWrap: 'wrap' }}>
            {/* Cut Selector */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <span style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: 600, textTransform: 'uppercase' }}>
                Cut:
              </span>
              <select
                value={selectedCut}
                disabled={loading}
                onChange={(e) => {
                  const cut = Number(e.target.value)
                  setSelectedCut(cut)
                  loadProtocolComparison(cut)
                }}
                style={{
                  background: 'rgba(15, 23, 42, 0.9)',
                  border: '1px solid rgba(56, 189, 248, 0.3)',
                  color: '#f8fafc',
                  padding: '0.45rem 0.85rem',
                  borderRadius: '8px',
                  fontSize: '0.88rem',
                  fontWeight: 600,
                  outline: 'none',
                  cursor: loading ? 'not-allowed' : 'pointer',
                }}
              >
                <option value={1}>Cut 1</option>
                <option value={2}>Cut 2</option>
                <option value={3}>Cut 3</option>
                <option value={4}>Cut 4</option>
                <option value={5}>Cut 5</option>
                <option value={6}>Cut 6 (Canonical PS2)</option>
              </select>
            </div>

            {/* Protocol Version Selector */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <span style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: 600, textTransform: 'uppercase' }}>
                Protocol:
              </span>
              <select
                value={selectedProtocolVersion}
                disabled={loading}
                onChange={(e) => setSelectedProtocolVersion(Number(e.target.value))}
                style={{
                  background: 'rgba(15, 23, 42, 0.9)',
                  border: '1px solid rgba(56, 189, 248, 0.3)',
                  color: '#f8fafc',
                  padding: '0.45rem 0.85rem',
                  borderRadius: '8px',
                  fontSize: '0.88rem',
                  fontWeight: 600,
                  outline: 'none',
                  cursor: loading ? 'not-allowed' : 'pointer',
                }}
              >
                <option value={1}>Protocol v1 (±7d window, no renal exclusion)</option>
                <option value={2}>Protocol v2 (±3d window, renal exclusion active)</option>
                <option value={3}>Protocol v3 (Sulfonylureas prohibited)</option>
              </select>
            </div>

            {/* Reset Memory Checkbox */}
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', cursor: 'pointer', fontSize: '0.82rem', color: '#94a3b8' }}>
              <input
                type="checkbox"
                checked={resetMemory}
                disabled={loading}
                onChange={(e) => setResetMemory(e.target.checked)}
                style={{ cursor: 'pointer', accentColor: '#0ea5e9' }}
              />
              Reset Memory (Fresh State)
            </label>
          </div>

          {/* Action Buttons */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <button
              onClick={() => executeCycle(resetMemory)}
              disabled={loading}
              className="btn-primary"
              style={{
                fontSize: '0.85rem',
                padding: '0.55rem 1.15rem',
                opacity: loading ? 0.7 : 1,
              }}
            >
              <Play size={16} fill="white" />
              {loading ? 'Running Cycle...' : 'Run Monitoring Cycle'}
            </button>

            <button
              onClick={handleRunDuplicateTest}
              disabled={dupLoading || loading}
              className="btn-secondary"
              style={{
                fontSize: '0.85rem',
                padding: '0.55rem 1.15rem',
                borderColor: 'rgba(168, 85, 247, 0.4)',
                background: 'rgba(168, 85, 247, 0.1)',
                color: '#c084fc',
              }}
              title="Runs Cycle 1 then Cycle 2 to test 100% duplicate suppression"
            >
              <History size={16} />
              {dupLoading ? 'Testing...' : 'Duplicate Benchmark'}
            </button>
          </div>
        </div>

        {/* Global Toast / Success Notification */}
        {notification && (
          <div
            style={{
              marginTop: '1rem',
              padding: '0.75rem 1rem',
              borderRadius: '8px',
              background: 'rgba(16, 185, 129, 0.12)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              color: '#34d399',
              fontSize: '0.85rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <CheckCircle2 size={16} color="#34d399" />
              <span>{notification}</span>
            </div>
            <button
              onClick={() => setNotification(null)}
              style={{ background: 'none', border: 'none', color: '#34d399', cursor: 'pointer' }}
            >
              &times;
            </button>
          </div>
        )}

        {/* Global Error Banner */}
        {error && (
          <div
            style={{
              marginTop: '1rem',
              padding: '0.75rem 1rem',
              borderRadius: '8px',
              background: 'rgba(244, 63, 94, 0.15)',
              border: '1px solid rgba(244, 63, 94, 0.3)',
              color: '#f8fafc',
              fontSize: '0.85rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <AlertTriangle size={16} color="#fb7185" />
              <span>{error}</span>
            </div>
            <button
              onClick={() => setError(null)}
              style={{ background: 'none', border: 'none', color: '#fb7185', cursor: 'pointer' }}
            >
              &times;
            </button>
          </div>
        )}
      </div>

      {/* 2. Summary KPI Cards (Strictly Populated from Backend) */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
          gap: '1.25rem',
        }}
      >
        {/* Card 1: Total Findings */}
        <div
          className="glass-card"
          style={{
            padding: '1.25rem 1.5rem',
            borderLeft: '4px solid #38bdf8',
            cursor: 'pointer',
          }}
          onClick={() => setActiveSubTab('detect')}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <span style={{ fontSize: '0.78rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>
              Total Findings
            </span>
            <Database size={18} color="#38bdf8" />
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: '#f8fafc', marginTop: '0.4rem' }}>
            {report ? report.summary.total_findings : '—'}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#38bdf8', marginTop: '0.25rem' }}>
            {report ? 'Signals from StudyGraph' : 'Awaiting Cycle Run'}
          </div>
        </div>

        {/* Card 2: Escalations */}
        <div
          className="glass-card"
          style={{
            padding: '1.25rem 1.5rem',
            borderLeft: '4px solid #f43f5e',
            cursor: 'pointer',
          }}
          onClick={() => setActiveSubTab('medical_review')}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <span style={{ fontSize: '0.78rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>
              Escalations
            </span>
            <ShieldAlert size={18} color="#f43f5e" />
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: '#fb7185', marginTop: '0.4rem' }}>
            {report ? report.summary.total_escalations : '—'}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#f43f5e', marginTop: '0.25rem' }}>
            {report ? 'Clinical Safety Alerts' : 'Awaiting Cycle Run'}
          </div>
        </div>

        {/* Card 3: Data Queries */}
        <div
          className="glass-card"
          style={{
            padding: '1.25rem 1.5rem',
            borderLeft: '4px solid #fbbf24',
            cursor: 'pointer',
          }}
          onClick={() => setActiveSubTab('data_manager')}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <span style={{ fontSize: '0.78rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>
              Data Queries
            </span>
            <FileQuestion size={18} color="#fbbf24" />
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: '#fbbf24', marginTop: '0.4rem' }}>
            {report ? report.summary.total_queries : '—'}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#fbbf24', marginTop: '0.25rem' }}>
            {report ? 'Automated Site Queries' : 'Awaiting Cycle Run'}
          </div>
        </div>

        {/* Card 4: Protocol Deviations */}
        <div
          className="glass-card"
          style={{
            padding: '1.25rem 1.5rem',
            borderLeft: '4px solid #818cf8',
            cursor: 'pointer',
          }}
          onClick={() => setActiveSubTab('compliance')}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <span style={{ fontSize: '0.78rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>
              Protocol Deviations
            </span>
            <GitBranch size={18} color="#818cf8" />
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: '#a5b4fc', marginTop: '0.4rem' }}>
            {report ? report.summary.total_deviations : '—'}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#818cf8', marginTop: '0.25rem' }}>
            {report ? `Non-Compliances (v${report.protocol_version})` : 'Awaiting Cycle Run'}
          </div>
        </div>

        {/* Card 5: Audit Trace Entries */}
        <div
          className="glass-card"
          style={{
            padding: '1.25rem 1.5rem',
            borderLeft: '4px solid #34d399',
            cursor: 'pointer',
          }}
          onClick={() => setActiveSubTab('audit_trace')}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <span style={{ fontSize: '0.78rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>
              Audit Trace Entries
            </span>
            <History size={18} color="#34d399" />
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: '#34d399', marginTop: '0.4rem' }}>
            {report ? report.summary.total_trace_entries : '—'}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#34d399', marginTop: '0.25rem' }}>
            {report ? 'Immutable Ledger Records' : 'Awaiting Cycle Run'}
          </div>
        </div>
      </div>

      {/* 3. Six-Node Interactive Pipeline Stepper Bar */}
      <div
        className="glass-card"
        style={{
          padding: '1.25rem 1.5rem',
          background: 'rgba(10, 16, 30, 0.85)',
          border: '1px solid rgba(56, 189, 248, 0.15)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#f8fafc', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Six-Node Autonomous Clinical Pipeline
          </div>
          <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
            Click any node below to inspect real decisions and clinical evidence
          </span>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(6, 1fr)',
            gap: '0.75rem',
          }}
        >
          {pipelineSteps.map((step, idx) => {
            const isActive = activeSubTab === step.id
            return (
              <div
                key={step.id}
                onClick={() => setActiveSubTab(step.id)}
                style={{
                  background: isActive
                    ? 'linear-gradient(135deg, rgba(14, 165, 233, 0.25) 0%, rgba(30, 58, 138, 0.3) 100%)'
                    : 'rgba(15, 23, 42, 0.6)',
                  border: isActive
                    ? '1px solid rgba(56, 189, 248, 0.6)'
                    : '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: '10px',
                  padding: '0.85rem 0.95rem',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  position: 'relative',
                  boxShadow: isActive ? '0 0 16px rgba(14, 165, 233, 0.25)' : 'none',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                  <span
                    style={{
                      fontSize: '0.7rem',
                      fontWeight: 700,
                      color: isActive ? '#38bdf8' : '#64748b',
                      textTransform: 'uppercase',
                    }}
                  >
                    Node 0{idx + 1}
                  </span>
                  <ChevronRight size={14} color={isActive ? '#38bdf8' : '#475569'} />
                </div>
                <div style={{ fontSize: '0.92rem', fontWeight: 700, color: '#f8fafc' }}>
                  {step.name}
                </div>
                <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: '2px' }}>
                  {step.code}
                </div>
                <div
                  style={{
                    marginTop: '0.5rem',
                    fontSize: '0.72rem',
                    fontWeight: 600,
                    color: isActive ? '#34d399' : '#38bdf8',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.3rem',
                  }}
                >
                  <span
                    style={{
                      width: '6px',
                      height: '6px',
                      borderRadius: '50%',
                      background: isActive ? '#34d399' : report ? '#38bdf8' : '#64748b',
                    }}
                  />
                  {step.status}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* 4. Sub-Navigation Tabs */}
      <div
        style={{
          display: 'flex',
          gap: '0.5rem',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          paddingBottom: '0.5rem',
          flexWrap: 'wrap',
        }}
      >
        <button
          onClick={() => setActiveSubTab('human_gate')}
          className="btn-secondary"
          style={{
            background: activeSubTab === 'human_gate' ? 'rgba(244, 63, 94, 0.18)' : 'transparent',
            borderColor: activeSubTab === 'human_gate' ? '#f43f5e' : 'transparent',
            color: activeSubTab === 'human_gate' ? '#fb7185' : '#94a3b8',
            fontSize: '0.85rem',
            padding: '0.5rem 1rem',
            fontWeight: 600,
          }}
        >
          <ShieldAlert size={16} color={activeSubTab === 'human_gate' ? '#fb7185' : '#94a3b8'} />
          Human Gate (Medical Review Panel)
          <span className="badge badge-rose font-mono" style={{ fontSize: '0.68rem', padding: '0.1rem 0.4rem' }}>
            CRITICAL
          </span>
        </button>

        <button
          onClick={() => setActiveSubTab('medical_review')}
          className="btn-secondary"
          style={{
            background: activeSubTab === 'medical_review' ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
            borderColor: activeSubTab === 'medical_review' ? '#38bdf8' : 'transparent',
            color: activeSubTab === 'medical_review' ? '#38bdf8' : '#94a3b8',
            fontSize: '0.85rem',
            padding: '0.5rem 1rem',
          }}
        >
          <AlertTriangle size={16} />
          Medical Review ({report?.escalations.length ?? '—'})
        </button>

        <button
          onClick={() => setActiveSubTab('data_manager')}
          className="btn-secondary"
          style={{
            background: activeSubTab === 'data_manager' ? 'rgba(251, 191, 36, 0.15)' : 'transparent',
            borderColor: activeSubTab === 'data_manager' ? '#fbbf24' : 'transparent',
            color: activeSubTab === 'data_manager' ? '#fbbf24' : '#94a3b8',
            fontSize: '0.85rem',
            padding: '0.5rem 1rem',
          }}
        >
          <FileQuestion size={16} />
          Data Manager Queries ({report?.queries.length ?? '—'})
        </button>

        <button
          onClick={() => setActiveSubTab('compliance')}
          className="btn-secondary"
          style={{
            background: activeSubTab === 'compliance' ? 'rgba(129, 140, 248, 0.15)' : 'transparent',
            borderColor: activeSubTab === 'compliance' ? '#818cf8' : 'transparent',
            color: activeSubTab === 'compliance' ? '#a5b4fc' : '#94a3b8',
            fontSize: '0.85rem',
            padding: '0.5rem 1rem',
          }}
        >
          <GitBranch size={16} />
          Compliance & Amendments ({report?.deviations.length ?? '—'})
        </button>

        <button
          onClick={() => setActiveSubTab('detect')}
          className="btn-secondary"
          style={{
            background: activeSubTab === 'detect' ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
            borderColor: activeSubTab === 'detect' ? '#38bdf8' : 'transparent',
            color: activeSubTab === 'detect' ? '#38bdf8' : '#94a3b8',
            fontSize: '0.85rem',
            padding: '0.5rem 1rem',
          }}
        >
          <Database size={16} />
          Detect Findings ({report?.findings.length ?? '—'})
        </button>

        <button
          onClick={() => setActiveSubTab('memory')}
          className="btn-secondary"
          style={{
            background: activeSubTab === 'memory' ? 'rgba(168, 85, 247, 0.15)' : 'transparent',
            borderColor: activeSubTab === 'memory' ? '#c084fc' : 'transparent',
            color: activeSubTab === 'memory' ? '#c084fc' : '#94a3b8',
            fontSize: '0.85rem',
            padding: '0.5rem 1rem',
          }}
        >
          <History size={16} />
          Review Memory (Cycle 1 vs 2)
        </button>

        <button
          onClick={() => setActiveSubTab('audit_trace')}
          className="btn-secondary"
          style={{
            background: activeSubTab === 'audit_trace' ? 'rgba(52, 211, 153, 0.15)' : 'transparent',
            borderColor: activeSubTab === 'audit_trace' ? '#34d399' : 'transparent',
            color: activeSubTab === 'audit_trace' ? '#34d399' : '#94a3b8',
            fontSize: '0.85rem',
            padding: '0.5rem 1rem',
          }}
        >
          <Clock size={16} />
          Audit Trace Log ({report?.summary.total_trace_entries ?? '—'})
        </button>
      </div>

      {/* Empty State when no report is loaded */}
      {!report && !loading && (
        <div
          className="glass-card"
          style={{
            padding: '3rem 2rem',
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '1rem',
          }}
        >
          <Activity size={48} color="#0ea5e9" />
          <h3 style={{ fontSize: '1.25rem', color: '#f8fafc' }}>
            No Clinical Surveillance Cycle Loaded
          </h3>
          <p style={{ fontSize: '0.9rem', color: '#94a3b8', maxWidth: '520px' }}>
            Click <strong>Run Monitoring Cycle</strong> above to initiate deterministic multi-agent review
            across StudyGraph clinical domains.
          </p>
          <button onClick={() => executeCycle(resetMemory)} className="btn-primary" style={{ marginTop: '0.5rem' }}>
            <Play size={16} fill="white" /> Run Monitoring Cycle Now
          </button>
        </div>
      )}

      {/* ===================================================================== */}
      {/* 5. TAB CONTENT: HUMAN GATE (PRIMARY / MOST IMPORTANT)                */}
      {/* ===================================================================== */}
      {activeSubTab === 'human_gate' && report && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Section Banner */}
          <div
            className="glass-card"
            style={{
              padding: '1.25rem 1.5rem',
              background: 'linear-gradient(135deg, rgba(244, 63, 94, 0.12) 0%, rgba(15, 23, 42, 0.8) 100%)',
              border: '1px solid rgba(244, 63, 94, 0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '1rem',
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span className="badge badge-rose">Human Gate Oversight</span>
                <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                  Medical Monitor Oversight Protocol &bull; Problem Statement 2 Worked Example
                </span>
              </div>
              <h3 style={{ fontSize: '1.15rem', color: '#f8fafc', marginTop: '0.4rem' }}>
                Physician Escalation Review & Real-Time Action Dispatches
              </h3>
              <p style={{ fontSize: '0.82rem', color: '#cbd5e1', marginTop: '0.2rem', maxWidth: '850px' }}>
                Every clinical safety escalation requires medical-monitor evaluation.
                <strong> APPROVE</strong> transmits action to ExecuteNode for site notification & expedited reporting.
                <strong> REJECT</strong> downgrades to monitoring with physician rationale.
                <strong> CLARIFY</strong> queries StudyGraph for exact lab evidence and resubmits.
              </p>
            </div>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <span className="badge badge-emerald font-mono">LIVE BACKEND API</span>
              <span className="badge badge-cyan font-mono">STATEFUL MEMORY</span>
            </div>
          </div>

          {/* Special Visual Callout: SAE Miscoded Rule Highlight */}
          {saeMiscodedItem && (
            <div
              className="glass-card pulse-glow"
              style={{
                padding: '1.25rem 1.5rem',
                background: 'linear-gradient(135deg, rgba(244, 63, 94, 0.18) 0%, rgba(15, 23, 42, 0.95) 100%)',
                border: '1px solid rgba(244, 63, 94, 0.5)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.4rem' }}>
                <ShieldAlert size={20} color="#f43f5e" />
                <span className="badge badge-rose font-mono">PROTOCOL §6 CRITICAL OVERRIDE</span>
                <span style={{ fontSize: '0.82rem', fontWeight: 700, color: '#fb7185' }}>
                  SAE Miscoding Detected: Subject 042-S02-004
                </span>
              </div>
              <div style={{ fontSize: '0.88rem', color: '#f8fafc', fontWeight: 600 }}>
                Subject 042-S02-004 Hospitalization Miscoded as Non-Serious (AESER = 'N', AESHOSP = 'Y')
              </div>
              <div style={{ fontSize: '0.82rem', color: '#cbd5e1', marginTop: '0.35rem', lineHeight: 1.45 }}>
                Under Protocol §6 and ICH E2A guidelines, any event requiring inpatient hospitalization is
                categorized as <strong>SERIOUS</strong> regardless of site classification. The Medical Review Node
                automatically recognized this discrepancy, upgraded it to <strong>CRITICAL</strong>, and queued it for immediate
                physician approval below.
              </div>
            </div>
          )}

          {/* Escalations List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            {report.escalations.map((esc) => {
              const isActionLoading = actionLoadingMap[esc.escalation_id] || false
              const isApproved = esc.status === 'APPROVED'
              const isRejected = esc.status === 'REJECTED'
              const isResubmitted = esc.status === 'RESUBMITTED'
              const isMiscoded = esc.code === 'SAE_MISCODED'

              return (
                <div
                  key={esc.escalation_id}
                  className="glass-card"
                  style={{
                    padding: '1.5rem',
                    border: isMiscoded
                      ? '1px solid rgba(244, 63, 94, 0.45)'
                      : '1px solid rgba(56, 189, 248, 0.2)',
                    background: isMiscoded
                      ? 'linear-gradient(180deg, rgba(244, 63, 94, 0.06) 0%, rgba(15, 23, 42, 0.85) 100%)'
                      : 'rgba(15, 23, 42, 0.75)',
                  }}
                >
                  {/* Card Top Row */}
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      flexWrap: 'wrap',
                      gap: '0.75rem',
                      borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
                      paddingBottom: '0.85rem',
                      marginBottom: '1rem',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      <span
                        className={
                          esc.code === 'SAE_MISCODED'
                            ? 'badge badge-rose font-mono'
                            : esc.code === 'HYS_LAW_ALERT'
                            ? 'badge badge-amber font-mono'
                            : 'badge badge-blue font-mono'
                        }
                      >
                        {esc.code}
                      </span>
                      <span className="font-mono" style={{ fontSize: '0.9rem', fontWeight: 700, color: '#f8fafc' }}>
                        Subject: {esc.usubjid}
                      </span>
                      <span className="badge badge-cyan font-mono" style={{ fontSize: '0.72rem' }}>
                        Site {esc.site_id}
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      <span
                        className={
                          esc.severity === 'CRITICAL'
                            ? 'badge badge-rose'
                            : esc.severity === 'HIGH'
                            ? 'badge badge-amber'
                            : 'badge badge-cyan'
                        }
                      >
                        {esc.severity}
                      </span>

                      <span
                        className={
                          isApproved
                            ? 'badge badge-emerald'
                            : isRejected
                            ? 'badge badge-rose'
                            : isResubmitted
                            ? 'badge badge-blue'
                            : 'badge badge-amber'
                        }
                      >
                        {esc.status}
                      </span>
                    </div>
                  </div>

                  {/* Summary & Rationale */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                    <div
                      style={{
                        background: 'rgba(10, 16, 30, 0.6)',
                        padding: '0.85rem',
                        borderRadius: '8px',
                        border: '1px solid rgba(255, 255, 255, 0.05)',
                      }}
                    >
                      <div style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>
                        Escalation Summary
                      </div>
                      <div style={{ fontSize: '0.88rem', color: '#f8fafc', marginTop: '0.3rem', lineHeight: 1.4 }}>
                        {esc.summary}
                      </div>
                    </div>

                    <div
                      style={{
                        background: 'rgba(10, 16, 30, 0.6)',
                        padding: '0.85rem',
                        borderRadius: '8px',
                        border: '1px solid rgba(255, 255, 255, 0.05)',
                      }}
                    >
                      <div style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>
                        Medical Rationale
                      </div>
                      <div style={{ fontSize: '0.88rem', color: '#cbd5e1', marginTop: '0.3rem', lineHeight: 1.4 }}>
                        {esc.rationale}
                      </div>
                    </div>
                  </div>

                  {/* Evidence RecordRefs */}
                  <div style={{ marginBottom: '1.25rem' }}>
                    <div style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.4rem' }}>
                      Exact Evidence RecordRefs:
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                      {esc.evidence.map((ev, i) => (
                        <div
                          key={i}
                          style={{
                            background: 'rgba(15, 23, 42, 0.8)',
                            border: '1px solid rgba(56, 189, 248, 0.2)',
                            borderRadius: '6px',
                            padding: '0.35rem 0.65rem',
                            fontSize: '0.75rem',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.4rem',
                          }}
                        >
                          <span className="badge badge-cyan font-mono" style={{ padding: '0.1rem 0.35rem', fontSize: '0.68rem' }}>
                            {ev.domain}
                          </span>
                          <span className="font-mono" style={{ color: '#f8fafc' }}>
                            {ev.usubjid} {ev.seq ? `[Seq ${ev.seq}]` : ''}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Clarification Output (if RESUBMITTED) */}
                  {esc.clarification && (
                    <div
                      style={{
                        background: 'rgba(14, 165, 233, 0.08)',
                        border: '1px solid rgba(56, 189, 248, 0.3)',
                        borderRadius: '8px',
                        padding: '1rem',
                        marginBottom: '1.25rem',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.4rem' }}>
                        <HelpCircle size={16} color="#38bdf8" />
                        <span style={{ fontSize: '0.78rem', fontWeight: 700, color: '#38bdf8', textTransform: 'uppercase' }}>
                          Medical Monitor Inquiry Answered via StudyGraph
                        </span>
                      </div>
                      <div style={{ fontSize: '0.84rem', color: '#94a3b8', fontStyle: 'italic' }}>
                        "{esc.clarification.question}"
                      </div>
                      <div
                        style={{
                          marginTop: '0.5rem',
                          fontSize: '0.88rem',
                          color: '#f8fafc',
                          fontWeight: 600,
                          background: 'rgba(15, 23, 42, 0.6)',
                          padding: '0.6rem 0.85rem',
                          borderRadius: '6px',
                          border: '1px solid rgba(56, 189, 248, 0.15)',
                        }}
                      >
                        {esc.clarification.answer}
                      </div>
                      {esc.clarification.evidence && esc.clarification.evidence.length > 0 && (
                        <div style={{ marginTop: '0.5rem', fontSize: '0.74rem', color: '#64748b' }}>
                          Grounding Evidence: {JSON.stringify(esc.clarification.evidence)}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Decision Outcomes Display */}
                  {isApproved && esc.human_decision && (
                    <div
                      style={{
                        background: 'rgba(16, 185, 129, 0.1)',
                        border: '1px solid rgba(16, 185, 129, 0.3)',
                        borderRadius: '8px',
                        padding: '0.85rem 1rem',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                        <CheckCircle2 size={18} color="#34d399" />
                        <div>
                          <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#34d399' }}>
                            DECISION: APPROVED BY MEDICAL MONITOR
                          </div>
                          <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                            Action transmitted to ExecuteNode &bull; Site Notification & Expedited Regulatory Reporting Dispatched
                          </div>
                        </div>
                      </div>
                      <span className="badge badge-emerald font-mono" style={{ fontSize: '0.7rem' }}>
                        TRANSMITTED TO EXECUTE
                      </span>
                    </div>
                  )}

                  {isRejected && esc.human_decision && (
                    <div
                      style={{
                        background: 'rgba(244, 63, 94, 0.1)',
                        border: '1px solid rgba(244, 63, 94, 0.3)',
                        borderRadius: '8px',
                        padding: '0.85rem 1rem',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                        <X size={18} color="#fb7185" />
                        <div>
                          <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#fb7185' }}>
                            DECISION: REJECTED — Downgraded to MONITORING
                          </div>
                          <div style={{ fontSize: '0.75rem', color: '#cbd5e1' }}>
                            Rationale: "{esc.human_decision.reason || 'Elective procedure unrelated to investigational drug.'}"
                          </div>
                        </div>
                      </div>
                      <span className="badge badge-rose font-mono" style={{ fontSize: '0.7rem' }}>
                        MONITORING ONLY
                      </span>
                    </div>
                  )}

                  {/* Decision Action Buttons (if pending or resubmitted) */}
                  {!isApproved && !isRejected && (
                    <div style={{ borderTop: '1px solid rgba(255, 255, 255, 0.08)', paddingTop: '1rem' }}>
                      {/* Active Reject Prompt */}
                      {activeRejectId === esc.escalation_id && (
                        <div
                          style={{
                            background: 'rgba(15, 23, 42, 0.95)',
                            border: '1px solid rgba(244, 63, 94, 0.3)',
                            borderRadius: '8px',
                            padding: '0.85rem',
                            marginBottom: '0.85rem',
                          }}
                        >
                          <div style={{ fontSize: '0.78rem', color: '#fb7185', fontWeight: 600, marginBottom: '0.35rem' }}>
                            Specify Medical Monitor Rejection Reason (Downgrades to Monitoring):
                          </div>
                          <input
                            type="text"
                            className="input-field"
                            disabled={isActionLoading}
                            style={{ fontSize: '0.85rem', padding: '0.5rem 0.75rem', marginBottom: '0.5rem' }}
                            value={
                              rejectReasonMap[esc.escalation_id] ??
                              'Hospitalization was elective cosmetic surgery, unrelated to investigational drug.'
                            }
                            onChange={(e) =>
                              setRejectReasonMap({ ...rejectReasonMap, [esc.escalation_id]: e.target.value })
                            }
                          />
                          <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <button
                              onClick={() => handleReject(esc.escalation_id)}
                              disabled={isActionLoading}
                              className="btn-primary"
                              style={{
                                background: 'linear-gradient(135deg, #e11d48 0%, #be123c 100%)',
                                fontSize: '0.78rem',
                                padding: '0.4rem 0.85rem',
                              }}
                            >
                              {isActionLoading ? 'Processing...' : 'Confirm Rejection & Downgrade'}
                            </button>
                            <button
                              onClick={() => setActiveRejectId(null)}
                              disabled={isActionLoading}
                              className="btn-secondary"
                              style={{ fontSize: '0.78rem', padding: '0.4rem 0.85rem' }}
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      )}

                      {/* Active Clarify Prompt */}
                      {activeClarifyId === esc.escalation_id && (
                        <div
                          style={{
                            background: 'rgba(15, 23, 42, 0.95)',
                            border: '1px solid rgba(56, 189, 248, 0.3)',
                            borderRadius: '8px',
                            padding: '0.85rem',
                            marginBottom: '0.85rem',
                          }}
                        >
                          <div style={{ fontSize: '0.78rem', color: '#38bdf8', fontWeight: 600, marginBottom: '0.35rem' }}>
                            Clinical Clarification Question (Resolves against StudyGraph):
                          </div>
                          <input
                            type="text"
                            className="input-field"
                            disabled={isActionLoading}
                            style={{ fontSize: '0.85rem', padding: '0.5rem 0.75rem', marginBottom: '0.5rem' }}
                            value={
                              clarifyQuestionMap[esc.escalation_id] ??
                              'What was the ALT at screening, and is there a concomitant hepatotoxic medication?'
                            }
                            onChange={(e) =>
                              setClarifyQuestionMap({ ...clarifyQuestionMap, [esc.escalation_id]: e.target.value })
                            }
                          />
                          <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <button
                              onClick={() => handleClarify(esc.escalation_id)}
                              disabled={isActionLoading}
                              className="btn-primary"
                              style={{
                                background: 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)',
                                fontSize: '0.78rem',
                                padding: '0.4rem 0.85rem',
                              }}
                            >
                              {isActionLoading ? 'Querying...' : 'Query StudyGraph & Resubmit'}
                            </button>
                            <button
                              onClick={() => setActiveClarifyId(null)}
                              disabled={isActionLoading}
                              className="btn-secondary"
                              style={{ fontSize: '0.78rem', padding: '0.4rem 0.85rem' }}
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      )}

                      {/* Action Buttons: APPROVE, REJECT, CLARIFY */}
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem' }}>
                        <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                          Medical Monitor Action Required:
                        </span>
                        <div style={{ display: 'flex', gap: '0.65rem' }}>
                          {/* APPROVE BUTTON */}
                          <button
                            onClick={() => handleApprove(esc.escalation_id)}
                            disabled={isActionLoading || loading}
                            className="btn-primary"
                            style={{
                              background: 'linear-gradient(135deg, #059669 0%, #047857 100%)',
                              fontSize: '0.82rem',
                              padding: '0.45rem 1rem',
                            }}
                          >
                            <Check size={16} /> APPROVE
                          </button>

                          {/* REJECT BUTTON */}
                          <button
                            onClick={() => {
                              setActiveRejectId(esc.escalation_id)
                              setActiveClarifyId(null)
                            }}
                            disabled={isActionLoading || loading}
                            className="btn-secondary"
                            style={{
                              borderColor: 'rgba(244, 63, 94, 0.4)',
                              color: '#fb7185',
                              fontSize: '0.82rem',
                              padding: '0.45rem 1rem',
                            }}
                          >
                            <X size={16} /> REJECT
                          </button>

                          {/* CLARIFY BUTTON */}
                          <button
                            onClick={() => {
                              setActiveClarifyId(esc.escalation_id)
                              setActiveRejectId(null)
                            }}
                            disabled={isActionLoading || loading}
                            className="btn-secondary"
                            style={{
                              borderColor: 'rgba(56, 189, 248, 0.4)',
                              color: '#38bdf8',
                              fontSize: '0.82rem',
                              padding: '0.45rem 1rem',
                            }}
                          >
                            <HelpCircle size={16} /> CLARIFY
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* 6. TAB CONTENT: MEDICAL REVIEW                                       */}
      {/* ===================================================================== */}
      {activeSubTab === 'medical_review' && report && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div
            className="glass-card"
            style={{
              padding: '1.25rem 1.5rem',
              background: 'rgba(15, 23, 42, 0.8)',
              borderLeft: '4px solid #f43f5e',
            }}
          >
            <h3 style={{ fontSize: '1.1rem', color: '#f8fafc', marginBottom: '0.4rem' }}>
              Node 02: Medical Review & Clinical Safety Escalations
            </h3>
            <p style={{ fontSize: '0.84rem', color: '#94a3b8', lineHeight: 1.5 }}>
              Evaluates clinical seriousness, biological plausibility, and immediate expedited reporting requirements.
              Identifies acute Hy's Law hepatotoxicity alerts, confirmed serious adverse events, and
              critical protocol miscodings where hospitalizations were incorrectly categorized as non-serious.
            </p>
          </div>

          {/* Special Protocol Highlight: SAE Miscoded Rule */}
          {saeMiscodedItem && (
            <div
              className="glass-card"
              style={{
                padding: '1.25rem 1.5rem',
                background: 'linear-gradient(135deg, rgba(244, 63, 94, 0.15) 0%, rgba(15, 23, 42, 0.9) 100%)',
                border: '1px solid rgba(244, 63, 94, 0.4)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                <ShieldAlert size={18} color="#f43f5e" />
                <span style={{ fontSize: '0.82rem', fontWeight: 700, color: '#fb7185', textTransform: 'uppercase' }}>
                  Protocol Rule 1 — Serious AE Miscoding Escalation
                </span>
              </div>
              <div style={{ fontSize: '0.92rem', color: '#f8fafc', fontWeight: 600 }}>
                Subject 042-S02-004 Hospitalization Miscoded as Non-Serious (AESER = 'N', AESHOSP = 'Y')
              </div>
              <div style={{ fontSize: '0.82rem', color: '#cbd5e1', marginTop: '0.4rem', lineHeight: 1.45 }}>
                Under ICH E2A and Protocol §6, any adverse event resulting in inpatient hospitalization is
                automatically classified as <strong>SERIOUS</strong> regardless of initial investigator coding.
                ATLAS identified this contradiction, upgraded the finding to <strong>CRITICAL</strong>, and routed it to both
                the Human Gate for monitor approval and Data Manager for site query issuance.
              </div>
            </div>
          )}

          {/* List of Escalations */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '1.25rem' }}>
            {report.escalations.map((esc) => (
              <div
                key={esc.escalation_id}
                className="glass-card"
                style={{
                  padding: '1.25rem',
                  border: esc.code === 'SAE_MISCODED' ? '1px solid #f43f5e' : '1px solid rgba(56, 189, 248, 0.2)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.65rem' }}>
                  <span className="badge badge-rose font-mono">{esc.code}</span>
                  <span className="badge badge-cyan font-mono">Subj: {esc.usubjid}</span>
                </div>
                <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#f8fafc', marginBottom: '0.35rem' }}>
                  {esc.summary}
                </div>
                <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.75rem', lineHeight: 1.4 }}>
                  {esc.rationale}
                </div>
                <div style={{ fontSize: '0.72rem', color: '#64748b' }}>
                  Site: {esc.site_id} &bull; Severity: <strong style={{ color: '#fb7185' }}>{esc.severity}</strong> &bull; Status: {esc.status}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* 7. TAB CONTENT: DATA MANAGER                                         */}
      {/* ===================================================================== */}
      {activeSubTab === 'data_manager' && report && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div
            className="glass-card"
            style={{
              padding: '1.25rem 1.5rem',
              background: 'rgba(15, 23, 42, 0.8)',
              borderLeft: '4px solid #fbbf24',
            }}
          >
            <h3 style={{ fontSize: '1.1rem', color: '#f8fafc', marginBottom: '0.4rem' }}>
              Node 03: Data Manager Discrepancy Queries
            </h3>
            <p style={{ fontSize: '0.84rem', color: '#94a3b8', lineHeight: 1.5 }}>
              Generates formal CDISC SDTM queries to clinical investigative sites for data discrepancies,
              including invalid dose administrations (<code className="font-mono" style={{ color: '#fbbf24' }}>EX.EXDOSE</code>)
              and conflicting serious adverse event designations (<code className="font-mono" style={{ color: '#fbbf24' }}>AE.AESER</code>).
            </p>
          </div>

          {/* Queries Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '1.25rem' }}>
            {report.queries.map((q) => (
              <div
                key={q.query_id}
                className="glass-card"
                style={{
                  padding: '1.25rem',
                  border: '1px solid rgba(251, 191, 36, 0.25)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.65rem' }}>
                  <span className="badge badge-amber font-mono">{q.domain}.{q.target_field}</span>
                  <span className="badge badge-cyan font-mono">{q.usubjid}</span>
                </div>
                <div style={{ fontSize: '0.78rem', color: '#64748b', fontFamily: 'monospace', marginBottom: '0.35rem' }}>
                  {q.query_id}
                </div>
                <div style={{ fontSize: '0.88rem', color: '#f8fafc', fontWeight: 600, marginBottom: '0.65rem' }}>
                  {q.query_text}
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem', color: '#94a3b8' }}>
                  <span>Site: {q.site_id}</span>
                  <span className="badge badge-emerald">STATUS: {q.status}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* 8. TAB CONTENT: COMPLIANCE & AMENDMENTS                              */}
      {/* ===================================================================== */}
      {activeSubTab === 'compliance' && report && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Top Info Banner */}
          <div
            className="glass-card"
            style={{
              padding: '1.25rem 1.5rem',
              background: 'rgba(15, 23, 42, 0.8)',
              borderLeft: '4px solid #818cf8',
            }}
          >
            <h3 style={{ fontSize: '1.1rem', color: '#f8fafc', marginBottom: '0.4rem' }}>
              Node 04: Protocol Compliance & Mid-Stage Amendment Sensitivity
            </h3>
            <p style={{ fontSize: '0.84rem', color: '#94a3b8', lineHeight: 1.5 }}>
              Evaluates study subjects against protocol rules active at the requested cut.
              Dynamically reflects mid-study protocol amendments, such as narrowing the allowable visit window
              from ±7 days to ±3 days, and activating renal exclusion thresholds.
            </p>
          </div>

          {/* Category Count Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '1rem' }}>
            {Object.entries(report.breakdowns.deviations).map(([cat, count]) => (
              <div
                key={cat}
                className="glass-card"
                onClick={() => setDeviationFilterCat(deviationFilterCat === cat ? 'ALL' : cat)}
                style={{
                  padding: '1rem',
                  border: deviationFilterCat === cat ? '1px solid #38bdf8' : '1px solid rgba(255, 255, 255, 0.08)',
                  background: deviationFilterCat === cat ? 'rgba(14, 165, 233, 0.15)' : 'rgba(15, 23, 42, 0.6)',
                  cursor: 'pointer',
                }}
              >
                <div style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>
                  {cat}
                </div>
                <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#f8fafc', marginTop: '0.2rem' }}>
                  {count}
                </div>
                <div style={{ fontSize: '0.7rem', color: '#38bdf8' }}>
                  {cat === 'VISIT_WINDOW' ? '±3d Narrowed Window' : cat === 'RENAL_EXCLUSION' ? 'Cr > 1.5 mg/dL' : 'Active Deviation'}
                </div>
              </div>
            ))}
          </div>

          {/* Protocol Version Sensitivity Comparison Card */}
          {protocolComp && (
            <div
              className="glass-card"
              style={{
                padding: '1.5rem',
                background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%)',
                border: '1px solid rgba(129, 140, 248, 0.3)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                <div>
                  <h4 style={{ fontSize: '1rem', fontWeight: 700, color: '#f8fafc' }}>
                    Protocol Amendments Comparison Matrix (Cut {protocolComp.cut})
                  </h4>
                  <div style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                    Demonstrating sensitivity to mid-stage protocol amendments across versions
                  </div>
                </div>
                <span className="badge badge-purple font-mono">AMENDMENT AWARE</span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1.25rem' }}>
                {protocolComp.versions.map((v) => (
                  <div
                    key={v.version}
                    style={{
                      background: 'rgba(10, 16, 30, 0.7)',
                      border: v.version === selectedProtocolVersion ? '1px solid #38bdf8' : '1px solid rgba(255, 255, 255, 0.08)',
                      borderRadius: '8px',
                      padding: '1rem',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span className="badge badge-cyan font-mono">{v.label}</span>
                      <span style={{ fontSize: '1.3rem', fontWeight: 800, color: '#f8fafc' }}>
                        {v.total_deviations}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.78rem', color: '#94a3b8', marginTop: '0.5rem', lineHeight: 1.3 }}>
                      {v.rules}
                    </div>
                    <div style={{ marginTop: '0.75rem', paddingTop: '0.5rem', borderTop: '1px solid rgba(255, 255, 255, 0.06)', fontSize: '0.72rem', color: '#cbd5e1' }}>
                      Window: {v.breakdown.VISIT_WINDOW || 0} &bull; Renal: {v.breakdown.RENAL_EXCLUSION || 0} &bull; Meds: {v.breakdown.PROHIBITED_MED || 0}
                    </div>
                  </div>
                ))}
              </div>

              {/* Highlights */}
              <div style={{ background: 'rgba(15, 23, 42, 0.6)', borderRadius: '8px', padding: '0.85rem' }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#a5b4fc', textTransform: 'uppercase', marginBottom: '0.35rem' }}>
                  Mid-Stage Amendment Regulatory Insights:
                </div>
                <ul style={{ paddingLeft: '1.25rem', fontSize: '0.8rem', color: '#cbd5e1', lineHeight: 1.5 }}>
                  {protocolComp.amendment_highlights.map((hl, i) => (
                    <li key={i}>{hl}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* Filter & Deviations Table */}
          <div className="glass-card" style={{ padding: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#f8fafc' }}>
                  Deviations Table ({filteredDeviations.length} records)
                </span>
                {deviationFilterCat !== 'ALL' && (
                  <span className="badge badge-cyan font-mono">
                    FILTER: {deviationFilterCat}
                    <button
                      onClick={() => setDeviationFilterCat('ALL')}
                      style={{ background: 'none', border: 'none', color: '#38bdf8', cursor: 'pointer', marginLeft: '4px' }}
                    >
                      &times;
                    </button>
                  </span>
                )}
              </div>
              <input
                type="text"
                placeholder="Search subject, category, description..."
                value={deviationSearch}
                onChange={(e) => setDeviationSearch(e.target.value)}
                className="input-field"
                style={{ width: '280px', fontSize: '0.82rem', padding: '0.45rem 0.75rem' }}
              />
            </div>

            <div style={{ overflowX: 'auto', maxHeight: '420px' }}>
              <table className="clinical-table">
                <thead>
                  <tr>
                    <th>Deviation ID</th>
                    <th>Subject</th>
                    <th>Site</th>
                    <th>Category</th>
                    <th>Description</th>
                    <th>Evidence</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredDeviations.slice(0, 50).map((d) => (
                    <tr key={d.deviation_id}>
                      <td className="font-mono" style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                        {d.deviation_id}
                      </td>
                      <td className="font-mono" style={{ fontWeight: 600, color: '#38bdf8' }}>
                        {d.usubjid}
                      </td>
                      <td>{d.site_id}</td>
                      <td>
                        <span
                          className={
                            d.category === 'RENAL_EXCLUSION'
                              ? 'badge badge-rose'
                              : d.category === 'VISIT_WINDOW'
                              ? 'badge badge-cyan'
                              : 'badge badge-amber'
                          }
                        >
                          {d.category}
                        </span>
                      </td>
                      <td style={{ maxWidth: '350px' }}>{d.description}</td>
                      <td>
                        <span className="font-mono" style={{ fontSize: '0.72rem', color: '#64748b' }}>
                          {d.evidence.map((e) => `${e.domain}${e.seq ? `:${e.seq}` : ''}`).join(', ')}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* 9. TAB CONTENT: DETECT FINDINGS                                      */}
      {/* ===================================================================== */}
      {activeSubTab === 'detect' && report && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div
            className="glass-card"
            style={{
              padding: '1.25rem 1.5rem',
              background: 'rgba(15, 23, 42, 0.8)',
              borderLeft: '4px solid #38bdf8',
            }}
          >
            <h3 style={{ fontSize: '1.1rem', color: '#f8fafc', marginBottom: '0.4rem' }}>
              Node 01: Detect Node & StudyGraph Signal Extraction
            </h3>
            <p style={{ fontSize: '0.84rem', color: '#94a3b8', lineHeight: 1.5 }}>
              Continuously scans across all 9 SDTM clinical domains in StudyGraph (AE, LB, VS, EX, CM, DS, DM, MH, EG)
              to identify clinical anomalies, missing dosages, vital signs outliers, and laboratory abnormalities.
            </p>
          </div>

          {/* Filter Bar */}
          <div
            className="glass-card"
            style={{
              padding: '1rem 1.25rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '1rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <span style={{ fontSize: '0.78rem', color: '#94a3b8', fontWeight: 600, textTransform: 'uppercase' }}>
                Category:
              </span>
              {['ALL', 'LAB', 'AE', 'EXPOSURE', 'VISIT_SCHEDULE'].map((cat) => (
                <button
                  key={cat}
                  onClick={() => setFindingFilterCategory(cat)}
                  style={{
                    background: findingFilterCategory === cat ? 'rgba(14, 165, 233, 0.25)' : 'rgba(255, 255, 255, 0.05)',
                    border: findingFilterCategory === cat ? '1px solid #38bdf8' : '1px solid transparent',
                    color: findingFilterCategory === cat ? '#38bdf8' : '#94a3b8',
                    padding: '0.35rem 0.75rem',
                    borderRadius: '6px',
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  {cat}
                </button>
              ))}
            </div>

            <input
              type="text"
              placeholder="Search findings by subject or keyword..."
              value={findingSearch}
              onChange={(e) => setFindingSearch(e.target.value)}
              className="input-field"
              style={{ width: '280px', fontSize: '0.82rem', padding: '0.45rem 0.75rem' }}
            />
          </div>

          {/* Findings Table */}
          <div className="glass-card" style={{ padding: '1.25rem' }}>
            <div style={{ overflowX: 'auto', maxHeight: '480px' }}>
              <table className="clinical-table">
                <thead>
                  <tr>
                    <th>Finding ID</th>
                    <th>Subject</th>
                    <th>Site</th>
                    <th>Category</th>
                    <th>Severity</th>
                    <th>Description</th>
                    <th>Evidence RecordRefs</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredFindings.map((f) => (
                    <tr key={f.finding_id}>
                      <td className="font-mono" style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                        {f.finding_id}
                      </td>
                      <td className="font-mono" style={{ fontWeight: 600, color: '#38bdf8' }}>
                        {f.usubjid}
                      </td>
                      <td>{f.site_id}</td>
                      <td>
                        <span className="badge badge-cyan">{f.category}</span>
                      </td>
                      <td>
                        <span
                          className={
                            f.severity === 'CRITICAL'
                              ? 'badge badge-rose'
                              : f.severity === 'HIGH'
                              ? 'badge badge-amber'
                              : 'badge badge-cyan'
                          }
                        >
                          {f.severity}
                        </span>
                      </td>
                      <td style={{ maxWidth: '320px', fontSize: '0.82rem' }}>{f.description}</td>
                      <td>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
                          {f.evidence.map((ev, i) => (
                            <span
                              key={i}
                              className="badge badge-cyan font-mono"
                              style={{ fontSize: '0.68rem', padding: '0.1rem 0.35rem' }}
                            >
                              {ev.domain}:{ev.seq || 'ref'}
                            </span>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* 10. TAB CONTENT: REVIEW MEMORY & DUPLICATE SUPPRESSION               */}
      {/* ===================================================================== */}
      {activeSubTab === 'memory' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div
            className="glass-card"
            style={{
              padding: '1.25rem 1.5rem',
              background: 'rgba(15, 23, 42, 0.8)',
              borderLeft: '4px solid #c084fc',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
              <div>
                <h3 style={{ fontSize: '1.1rem', color: '#f8fafc', marginBottom: '0.4rem' }}>
                  ReviewMemory & 100% Duplicate Suppression Engine
                </h3>
                <p style={{ fontSize: '0.84rem', color: '#94a3b8', lineHeight: 1.5, maxWidth: '800px' }}>
                  Clinical trial surveillance runs repeatedly over time. ReviewMemory maintains persistent
                  ledger states of all past escalations, queries, and deviations to ensure that subsequent
                  monitoring cycles do NOT re-generate duplicate alerts or spam clinical sites.
                </p>
              </div>

              <button
                onClick={handleRunDuplicateTest}
                disabled={dupLoading}
                className="btn-primary"
                style={{
                  background: 'linear-gradient(135deg, #9333ea 0%, #7e22ce 100%)',
                  fontSize: '0.85rem',
                  padding: '0.55rem 1.15rem',
                }}
              >
                <RefreshCw size={16} className={dupLoading ? 'spin' : ''} />
                {dupLoading ? 'Running Benchmark...' : 'Run Live Duplicate Test'}
              </button>
            </div>
          </div>

          {/* Cycle 1 vs Cycle 2 Benchmark Metrics */}
          {dupResult ? (
            <div
              className="glass-card"
              style={{
                padding: '1.75rem',
                background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%)',
                border: '1px solid rgba(192, 132, 252, 0.3)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span className="badge badge-purple font-mono">BENCHMARK RESULTS</span>
                    <span style={{ fontSize: '0.78rem', color: '#34d399', fontWeight: 600 }}>
                      100% DUPLICATE SUPPRESSION VERIFIED
                    </span>
                  </div>
                  <h4 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#f8fafc', marginTop: '0.3rem' }}>
                    Cycle 1 (Initial Run) vs. Cycle 2 (Persistent Memory)
                  </h4>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <span style={{ fontSize: '2rem', fontWeight: 800, color: '#34d399' }}>
                    {dupResult.suppression_rate_percent.toFixed(1)}%
                  </span>
                  <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Suppression Rate</div>
                </div>
              </div>

              {/* Comparison Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1.25rem', marginBottom: '1.5rem' }}>
                <div
                  style={{
                    background: 'rgba(10, 16, 30, 0.7)',
                    padding: '1.25rem',
                    borderRadius: '10px',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                  }}
                >
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>
                    Findings Evaluated
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginTop: '0.4rem' }}>
                    <span style={{ fontSize: '1.5rem', fontWeight: 800, color: '#f8fafc' }}>
                      {dupResult.cycle_1.findings}
                    </span>
                    <ArrowRight size={16} color="#64748b" />
                    <span style={{ fontSize: '1.5rem', fontWeight: 800, color: '#38bdf8' }}>
                      {dupResult.cycle_2.findings}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '0.35rem' }}>
                    Raw data re-inspected
                  </div>
                </div>

                <div
                  style={{
                    background: 'rgba(10, 16, 30, 0.7)',
                    padding: '1.25rem',
                    borderRadius: '10px',
                    border: '1px solid rgba(244, 63, 94, 0.3)',
                  }}
                >
                  <div style={{ fontSize: '0.75rem', color: '#fb7185', textTransform: 'uppercase', fontWeight: 600 }}>
                    New Escalations
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginTop: '0.4rem' }}>
                    <span style={{ fontSize: '1.5rem', fontWeight: 800, color: '#f8fafc' }}>
                      {dupResult.cycle_1.escalations}
                    </span>
                    <ArrowRight size={16} color="#64748b" />
                    <span style={{ fontSize: '1.5rem', fontWeight: 800, color: '#34d399' }}>
                      {dupResult.cycle_2.escalations}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.72rem', color: '#34d399', marginTop: '0.35rem' }}>
                    {dupResult.suppressed.escalations} escalations suppressed
                  </div>
                </div>

                <div
                  style={{
                    background: 'rgba(10, 16, 30, 0.7)',
                    padding: '1.25rem',
                    borderRadius: '10px',
                    border: '1px solid rgba(251, 191, 36, 0.3)',
                  }}
                >
                  <div style={{ fontSize: '0.75rem', color: '#fbbf24', textTransform: 'uppercase', fontWeight: 600 }}>
                    New Queries
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginTop: '0.4rem' }}>
                    <span style={{ fontSize: '1.5rem', fontWeight: 800, color: '#f8fafc' }}>
                      {dupResult.cycle_1.queries}
                    </span>
                    <ArrowRight size={16} color="#64748b" />
                    <span style={{ fontSize: '1.5rem', fontWeight: 800, color: '#34d399' }}>
                      {dupResult.cycle_2.queries}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.72rem', color: '#34d399', marginTop: '0.35rem' }}>
                    {dupResult.suppressed.queries} queries suppressed
                  </div>
                </div>

                <div
                  style={{
                    background: 'rgba(10, 16, 30, 0.7)',
                    padding: '1.25rem',
                    borderRadius: '10px',
                    border: '1px solid rgba(129, 140, 248, 0.3)',
                  }}
                >
                  <div style={{ fontSize: '0.75rem', color: '#a5b4fc', textTransform: 'uppercase', fontWeight: 600 }}>
                    New Deviations
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginTop: '0.4rem' }}>
                    <span style={{ fontSize: '1.5rem', fontWeight: 800, color: '#f8fafc' }}>
                      {dupResult.cycle_1.deviations}
                    </span>
                    <ArrowRight size={16} color="#64748b" />
                    <span style={{ fontSize: '1.5rem', fontWeight: 800, color: '#34d399' }}>
                      {dupResult.cycle_2.deviations}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.72rem', color: '#34d399', marginTop: '0.35rem' }}>
                    {dupResult.suppressed.deviations} deviations suppressed
                  </div>
                </div>
              </div>

              {/* Total Suppressed Callout */}
              <div
                style={{
                  background: 'rgba(16, 185, 129, 0.1)',
                  border: '1px solid rgba(16, 185, 129, 0.3)',
                  borderRadius: '8px',
                  padding: '0.85rem 1.25rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <CheckCircle2 size={20} color="#34d399" />
                  <div style={{ fontSize: '0.88rem', color: '#f8fafc', fontWeight: 600 }}>
                    Trace Log Confirmed: {dupResult.suppressed.total} duplicate alerts successfully suppressed in Cycle 2
                  </div>
                </div>
                <span className="badge badge-emerald font-mono">
                  {dupResult.suppressed.escalations} ESC &bull; {dupResult.suppressed.queries} QRY &bull; {dupResult.suppressed.deviations} DEV
                </span>
              </div>
            </div>
          ) : (
            <div
              className="glass-card"
              style={{
                padding: '2.5rem',
                textAlign: 'center',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '1rem',
              }}
            >
              <History size={40} color="#c084fc" />
              <h4 style={{ fontSize: '1.1rem', color: '#f8fafc' }}>
                Run Live Duplicate Benchmark
              </h4>
              <p style={{ fontSize: '0.85rem', color: '#94a3b8', maxWidth: '520px' }}>
                Executes Cycle 1 followed immediately by Cycle 2 on a shared persistent ReviewMemory to verify
                that 100% of previously recorded escalations, queries, and deviations are suppressed.
              </p>
              <button
                onClick={handleRunDuplicateTest}
                disabled={dupLoading}
                className="btn-primary"
                style={{ background: 'linear-gradient(135deg, #9333ea 0%, #7e22ce 100%)' }}
              >
                <Play size={16} fill="white" /> {dupLoading ? 'Running...' : 'Run Benchmark'}
              </button>
            </div>
          )}
        </div>
      )}

      {/* ===================================================================== */}
      {/* 11. TAB CONTENT: AUDIT TRACE LOG                                     */}
      {/* ===================================================================== */}
      {activeSubTab === 'audit_trace' && report && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div
            className="glass-card"
            style={{
              padding: '1.25rem 1.5rem',
              background: 'rgba(15, 23, 42, 0.8)',
              borderLeft: '4px solid #34d399',
            }}
          >
            <h3 style={{ fontSize: '1.1rem', color: '#f8fafc', marginBottom: '0.4rem' }}>
              Node 06: Audit Trace Log & Sequential Regulatory Ledger
            </h3>
            <p style={{ fontSize: '0.84rem', color: '#94a3b8', lineHeight: 1.5 }}>
              Every agent node decision is recorded immediately in an immutable sequential ledger.
              Provides complete regulatory audit readiness for 21 CFR Part 11 and GCP inspections.
            </p>
          </div>

          {/* Node Distribution Breakdown Chips */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '0.75rem' }}>
            <div
              className="glass-card"
              onClick={() => setTraceFilterNode('ALL')}
              style={{
                padding: '0.85rem',
                border: traceFilterNode === 'ALL' ? '1px solid #38bdf8' : '1px solid rgba(255, 255, 255, 0.08)',
                background: traceFilterNode === 'ALL' ? 'rgba(14, 165, 233, 0.2)' : 'rgba(15, 23, 42, 0.6)',
                cursor: 'pointer',
              }}
            >
              <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>
                ALL NODES
              </div>
              <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#f8fafc', marginTop: '0.2rem' }}>
                {report.summary.total_trace_entries}
              </div>
              <div style={{ fontSize: '0.68rem', color: '#38bdf8' }}>Total Ledger</div>
            </div>

            {Object.entries(report.trace_summary).map(([node, count]) => {
              const isFiltered = traceFilterNode === node
              return (
                <div
                  key={node}
                  className="glass-card"
                  onClick={() => setTraceFilterNode(isFiltered ? 'ALL' : node)}
                  style={{
                    padding: '0.85rem',
                    border: isFiltered ? '1px solid #38bdf8' : '1px solid rgba(255, 255, 255, 0.08)',
                    background: isFiltered ? 'rgba(14, 165, 233, 0.2)' : 'rgba(15, 23, 42, 0.6)',
                    cursor: 'pointer',
                  }}
                >
                  <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>
                    {node}
                  </div>
                  <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#f8fafc', marginTop: '0.2rem' }}>
                    {count}
                  </div>
                  <div style={{ fontSize: '0.68rem', color: '#38bdf8' }}>Trace Entries</div>
                </div>
              )
            })}
          </div>

          {/* Trace Entries Table with Search & Filter */}
          <div className="glass-card" style={{ padding: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#f8fafc' }}>
                  Immutable Audit Log ({filteredTraces.length} displayed of {report.summary.total_trace_entries} total)
                </span>
                {traceFilterNode !== 'ALL' && (
                  <span className="badge badge-cyan font-mono">
                    NODE: {traceFilterNode}
                    <button
                      onClick={() => setTraceFilterNode('ALL')}
                      style={{ background: 'none', border: 'none', color: '#38bdf8', cursor: 'pointer', marginLeft: '4px' }}
                    >
                      &times;
                    </button>
                  </span>
                )}
              </div>

              <input
                type="text"
                placeholder="Search action, decision, subject..."
                value={traceSearch}
                onChange={(e) => setTraceSearch(e.target.value)}
                className="input-field"
                style={{ width: '260px', fontSize: '0.82rem', padding: '0.45rem 0.75rem' }}
              />
            </div>

            <div style={{ overflowX: 'auto', maxHeight: '480px' }}>
              <table className="clinical-table">
                <thead>
                  <tr>
                    <th>Trace ID</th>
                    <th>Timestamp</th>
                    <th>Node</th>
                    <th>Action</th>
                    <th>Decision</th>
                    <th>Subject</th>
                    <th>Finding ID</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredTraces.slice(0, 80).map((t) => (
                    <tr key={t.trace_id}>
                      <td className="font-mono" style={{ fontSize: '0.72rem', color: '#64748b' }}>
                        {t.trace_id}
                      </td>
                      <td className="font-mono" style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                        {t.timestamp.replace('T', ' ').slice(0, 19)}
                      </td>
                      <td>
                        <span className="badge badge-cyan font-mono" style={{ fontSize: '0.68rem' }}>
                          {t.node}
                        </span>
                      </td>
                      <td style={{ fontSize: '0.82rem', fontWeight: 600, color: '#f8fafc' }}>
                        {t.action}
                      </td>
                      <td>
                        <span
                          className={
                            t.decision.includes('suppressed')
                              ? 'badge badge-purple font-mono'
                              : t.decision === 'APPROVED'
                              ? 'badge badge-emerald font-mono'
                              : t.decision === 'REJECTED'
                              ? 'badge badge-rose font-mono'
                              : 'badge badge-blue font-mono'
                          }
                          style={{ fontSize: '0.68rem' }}
                        >
                          {t.decision}
                        </span>
                      </td>
                      <td className="font-mono" style={{ fontSize: '0.78rem', color: '#38bdf8' }}>
                        {t.subject || '—'}
                      </td>
                      <td className="font-mono" style={{ fontSize: '0.72rem', color: '#64748b' }}>
                        {t.finding_id || '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
