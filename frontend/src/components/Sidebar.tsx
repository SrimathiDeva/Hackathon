import React from 'react'
import {
  LayoutDashboard,
  User,
  HelpCircle,
  AlertTriangle,
  GitBranch,
  CheckCircle2,
  Activity,
} from 'lucide-react'

export type NavTab = 'dashboard' | 'patient' | 'ask' | 'findings' | 'protocol' | 'validation'

interface SidebarProps {
  activeTab: NavTab
  setActiveTab: (tab: NavTab) => void
  isBackendHealthy: boolean
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  isBackendHealthy,
}) => {
  const navItems: Array<{ id: NavTab; label: string; icon: React.ReactNode }> = [
    { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard size={18} /> },
    { id: 'patient', label: 'Patient 360', icon: <User size={18} /> },
    { id: 'ask', label: 'Ask ATLAS', icon: <HelpCircle size={18} /> },
    { id: 'findings', label: "Hy's Law", icon: <AlertTriangle size={18} /> },
    { id: 'protocol', label: 'Protocol', icon: <GitBranch size={18} /> },
    { id: 'validation', label: 'Validation', icon: <CheckCircle2 size={18} /> },
  ]

  return (
    <aside
      style={{
        width: '260px',
        backgroundColor: 'rgba(10, 16, 30, 0.95)',
        backdropFilter: 'blur(20px)',
        borderRight: '1px solid rgba(56, 189, 248, 0.12)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: '1.5rem 1rem',
        height: '100vh',
        position: 'sticky',
        top: 0,
        zIndex: 40,
      }}
    >
      <div>
        {/* Brand Header */}
        <div style={{ padding: '0.5rem 0.75rem', marginBottom: '2rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <div
              style={{
                width: '38px',
                height: '38px',
                borderRadius: '10px',
                background: 'linear-gradient(135deg, #0ea5e9 0%, #3b82f6 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 4px 12px rgba(14, 165, 233, 0.4)',
              }}
            >
              <Activity size={22} color="#ffffff" />
            </div>
            <div>
              <h1 style={{ fontSize: '1.25rem', fontWeight: 800, letterSpacing: '0.04em', color: '#f8fafc', lineHeight: 1.1 }}>
                ATLAS
              </h1>
              <span
                style={{
                  fontSize: '0.72rem',
                  fontWeight: 600,
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase',
                  color: '#38bdf8',
                }}
              >
                Study Sentinel
              </span>
            </div>
          </div>
          <div
            style={{
              fontSize: '0.7rem',
              color: '#64748b',
              marginTop: '0.65rem',
              borderTop: '1px solid rgba(255, 255, 255, 0.06)',
              paddingTop: '0.5rem',
            }}
          >
            Clinical Trial Intelligence
          </div>
        </div>

        {/* Navigation Items */}
        <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
          {navItems.map((item) => {
            const isActive = activeTab === item.id
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem',
                  padding: '0.7rem 0.9rem',
                  borderRadius: '10px',
                  border: isActive
                    ? '1px solid rgba(56, 189, 248, 0.35)'
                    : '1px solid transparent',
                  background: isActive
                    ? 'linear-gradient(90deg, rgba(14, 165, 233, 0.18) 0%, rgba(99, 102, 241, 0.08) 100%)'
                    : 'transparent',
                  color: isActive ? '#38bdf8' : '#94a3b8',
                  fontWeight: isActive ? 600 : 500,
                  fontSize: '0.9rem',
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'all 0.18s ease',
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.color = '#f8fafc'
                    e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.04)'
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.color = '#94a3b8'
                    e.currentTarget.style.backgroundColor = 'transparent'
                  }
                }}
              >
                <span style={{ color: isActive ? '#38bdf8' : '#64748b' }}>{item.icon}</span>
                {item.label}
              </button>
            )
          })}
        </nav>
      </div>

      {/* Backend Status Footer */}
      <div
        style={{
          padding: '0.85rem',
          borderRadius: '10px',
          background: 'rgba(15, 23, 42, 0.6)',
          border: '1px solid rgba(255, 255, 255, 0.06)',
          display: 'flex',
          alignItems: 'center',
          gap: '0.65rem',
        }}
      >
        <div
          style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: isBackendHealthy ? '#10b981' : '#f43f5e',
            boxShadow: isBackendHealthy
              ? '0 0 8px #10b981'
              : '0 0 8px #f43f5e',
          }}
        />
        <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
          <div style={{ fontWeight: 600, color: isBackendHealthy ? '#f8fafc' : '#f43f5e' }}>
            {isBackendHealthy ? 'ATLAS Engine Ready' : 'Backend Offline'}
          </div>
          <div style={{ fontSize: '0.68rem', color: '#64748b' }}>FastAPI :8000</div>
        </div>
      </div>
    </aside>
  )
}
