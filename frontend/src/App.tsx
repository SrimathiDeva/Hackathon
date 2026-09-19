import { useState, useEffect } from 'react'
import { Sidebar } from './components/Sidebar'
import type { NavTab } from './components/Sidebar'
import { QueryWorkbenchView } from './components/QueryWorkbenchView'
import { DashboardView } from './components/DashboardView'
import { Patient360View } from './components/Patient360View'
import { AskAtlasView } from './components/AskAtlasView'
import { HysLawView } from './components/HysLawView'
import { ProtocolView } from './components/ProtocolView'
import { ValidationView } from './components/ValidationView'
import { MonitorDashboardView } from './components/MonitorDashboardView'
import { KnowledgeGraphView } from './components/KnowledgeGraphView'
import { fetchHealth, fetchStats } from './api'
import type { StudyStats } from './types'
import { AlertCircle } from 'lucide-react'

export function App() {
  const [activeTab, setActiveTab] = useState<NavTab>('monitor')
  const [selectedSubject, setSelectedSubject] = useState<string>('042-S07-001')
  const [isBackendHealthy, setIsBackendHealthy] = useState<boolean>(false)
  const [stats, setStats] = useState<StudyStats | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const handleNavigateToPatient = (usubjid: string) => {
    setSelectedSubject(usubjid)
    setActiveTab('patient')
  }

  const checkBackend = async () => {
    try {
      await fetchHealth()
      setIsBackendHealthy(true)
      setErrorMessage(null)
      const st = await fetchStats()
      setStats(st)
    } catch {
      setIsBackendHealthy(false)
      setErrorMessage('ATLAS service unavailable. Please check that the backend is running at http://127.0.0.1:8001.')
    }
  }

  useEffect(() => {
    checkBackend()
    const interval = setInterval(checkBackend, 15000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: 'var(--bg-primary)' }}>
      {/* Fixed Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        isBackendHealthy={isBackendHealthy}
      />

      {/* Main Content Area */}
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        {/* Top Header Bar */}
        <header
          style={{
            height: '60px',
            borderBottom: '1px solid rgba(56, 189, 248, 0.1)',
            background: 'rgba(10, 16, 30, 0.8)',
            backdropFilter: 'blur(16px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 2.5rem',
            position: 'sticky',
            top: 0,
            zIndex: 30,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span style={{ fontSize: '0.9rem', color: '#94a3b8', textTransform: 'capitalize' }}>
              ATLAS Dashboard
            </span>
            <span style={{ color: '#64748b' }}>/</span>
            <span style={{ fontSize: '0.9rem', color: '#38bdf8', fontWeight: 600, textTransform: 'capitalize' }}>
              {activeTab === 'monitor'
                ? 'PS2 MONITOR Surveillance'
                : activeTab === 'knowledge-graph'
                ? 'Knowledge Graph Visualization'
                : activeTab === 'query'
                ? 'Query Workbench'
                : activeTab === 'findings'
                ? "Hy's Law"
                : activeTab}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <span className="badge badge-cyan font-mono" style={{ fontSize: '0.75rem' }}>
              STUDY-042
            </span>
            <span className="badge badge-emerald" style={{ fontSize: '0.75rem' }}>
              Deterministic Python
            </span>
          </div>
        </header>

        {/* Global Error Banner if backend offline */}
        {errorMessage && (
          <div
            style={{
              background: 'rgba(244, 63, 94, 0.15)',
              borderBottom: '1px solid rgba(244, 63, 94, 0.3)',
              color: '#f8fafc',
              padding: '0.75rem 2.5rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              fontSize: '0.88rem',
            }}
          >
            <AlertCircle size={18} color="#f43f5e" />
            <div>{errorMessage}</div>
          </div>
        )}

        {/* Page Content View */}
        <div style={{ flex: 1, padding: '2.5rem', overflowY: 'auto' }}>
          {activeTab === 'monitor' && <MonitorDashboardView />}
          {activeTab === 'knowledge-graph' && <KnowledgeGraphView />}
          {activeTab === 'query' && (
            <QueryWorkbenchView onNavigateToPatient={handleNavigateToPatient} />
          )}
          {activeTab === 'dashboard' && (
            <DashboardView stats={stats} setActiveTab={setActiveTab} />
          )}
          {activeTab === 'patient' && (
            <Patient360View initialSubject={selectedSubject} />
          )}
          {activeTab === 'ask' && <AskAtlasView />}
          {activeTab === 'findings' && <HysLawView />}
          {activeTab === 'protocol' && <ProtocolView />}
          {activeTab === 'validation' && <ValidationView />}
        </div>

        {/* Footer */}
        <footer
          style={{
            padding: '1.25rem 2.5rem',
            borderTop: '1px solid rgba(255, 255, 255, 0.05)',
            background: 'rgba(7, 11, 20, 0.95)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: '0.78rem',
            color: '#64748b',
          }}
        >
          <div>
            ATLAS — Clinical Sentinel (Problem Statement 1 & 2 MONITOR) &bull; Hackathon Submission
          </div>
          <div>
            Grounded RecordRef Evidence &bull; Multi-Agent Deterministic Engine
          </div>
        </footer>
      </main>
    </div>
  )
}

export default App
