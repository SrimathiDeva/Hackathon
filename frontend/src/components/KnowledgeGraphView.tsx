import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import {
  Search,
  ZoomIn,
  ZoomOut,
  Maximize2,
  RotateCcw,
  Share2,
  ShieldAlert,
  AlertTriangle,
  Activity,
  FileText,
  User,
  GitBranch,
  Calendar,
  CheckCircle,
  Filter,
  Layers,
  Sparkles,
} from 'lucide-react'
import { fetchKnowledgeGraph, fetchPatientsList } from '../api'
import type { GraphNode, KnowledgeGraphData, GraphNodeType } from '../types'

// Node type styling configurations
const NODE_CONFIG: Record<
  GraphNodeType,
  { label: string; color: string; border: string; bg: string; icon: React.ReactNode }
> = {
  study: {
    label: 'Study Protocol',
    color: '#38bdf8',
    border: 'rgba(56, 189, 248, 0.6)',
    bg: 'rgba(56, 189, 248, 0.15)',
    icon: <Activity size={14} color="#38bdf8" />,
  },
  protocol: {
    label: 'Protocol Rule',
    color: '#60a5fa',
    border: 'rgba(96, 165, 250, 0.6)',
    bg: 'rgba(96, 165, 250, 0.14)',
    icon: <GitBranch size={14} color="#60a5fa" />,
  },
  subject: {
    label: 'Subject',
    color: '#0ea5e9',
    border: 'rgba(14, 165, 233, 0.6)',
    bg: 'rgba(14, 165, 233, 0.14)',
    icon: <User size={14} color="#0ea5e9" />,
  },
  finding: {
    label: 'Clinical Finding',
    color: '#f59e0b',
    border: 'rgba(245, 158, 11, 0.7)',
    bg: 'rgba(245, 158, 11, 0.16)',
    icon: <AlertTriangle size={14} color="#f59e0b" />,
  },
  evidence: {
    label: 'RecordRef Evidence',
    color: '#fbbf24',
    border: 'rgba(251, 191, 36, 0.7)',
    bg: 'rgba(251, 191, 36, 0.15)',
    icon: <FileText size={14} color="#fbbf24" />,
  },
  lab: {
    label: 'Laboratory (LB)',
    color: '#a855f7',
    border: 'rgba(168, 85, 247, 0.6)',
    bg: 'rgba(168, 85, 247, 0.14)',
    icon: <Activity size={14} color="#a855f7" />,
  },
  adverse_event: {
    label: 'Adverse Event (AE)',
    color: '#f43f5e',
    border: 'rgba(244, 63, 94, 0.6)',
    bg: 'rgba(244, 63, 94, 0.14)',
    icon: <ShieldAlert size={14} color="#f43f5e" />,
  },
  exposure: {
    label: 'Exposure / Dose (EX)',
    color: '#10b981',
    border: 'rgba(168, 85, 247, 0.6)',
    bg: 'rgba(16, 185, 129, 0.14)',
    icon: <CheckCircle size={14} color="#10b981" />,
  },
  visit: {
    label: 'Study Visit',
    color: '#14b8a6',
    border: 'rgba(20, 184, 166, 0.6)',
    bg: 'rgba(20, 184, 166, 0.14)',
    icon: <Calendar size={14} color="#14b8a6" />,
  },
  escalation: {
    label: 'Medical Escalation',
    color: '#ec4899',
    border: 'rgba(236, 72, 153, 0.7)',
    bg: 'rgba(236, 72, 153, 0.16)',
    icon: <ShieldAlert size={14} color="#ec4899" />,
  },
  query: {
    label: 'Data Query',
    color: '#8b5cf6',
    border: 'rgba(139, 92, 246, 0.6)',
    bg: 'rgba(139, 92, 246, 0.14)',
    icon: <FileText size={14} color="#8b5cf6" />,
  },
  clinical_record: {
    label: 'Clinical Record',
    color: '#94a3b8',
    border: 'rgba(148, 163, 184, 0.5)',
    bg: 'rgba(148, 163, 184, 0.12)',
    icon: <FileText size={14} color="#94a3b8" />,
  },
}

export const KnowledgeGraphView: React.FC = () => {
  const [graphData, setGraphData] = useState<KnowledgeGraphData | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  // Filtering & Search
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [activePreset, setActivePreset] = useState<string>('hys-003')
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [allSubjects, setAllSubjects] = useState<string[]>([])

  // Selection & Trace
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null)
  const [tracedNodeIds, setTracedNodeIds] = useState<Set<string>>(new Set())

  // Viewport Pan & Zoom
  const [zoom, setZoom] = useState<number>(0.9)
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 80, y: 50 })
  const [isPanning, setIsPanning] = useState<boolean>(false)
  const [panStart, setPanStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 })

  // Node Dragging
  const [draggingNodeId, setDraggingNodeId] = useState<string | null>(null)
  const [dragOffset, setDragOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 })
  const [customPositions, setCustomPositions] = useState<Record<string, { x: number; y: number }>>({})

  const svgRef = useRef<SVGSVGElement | null>(null)

  // Load subject list for search autocomplete
  useEffect(() => {
    fetchPatientsList()
      .then((data) => setAllSubjects(data.subjects || []))
      .catch(() => {})
  }, [])

  // Load graph data based on query / preset
  const loadGraph = useCallback(
    async (params?: { usubjid?: string; finding_id?: string; record_ref?: string }) => {
      setLoading(true)
      setError(null)
      try {
        const data = await fetchKnowledgeGraph({
          ...params,
          cut: 6,
          protocol_version: 2,
        })
        setGraphData(data)
        setTracedNodeIds(new Set())
        setCustomPositions({})

        // Default select the most prominent finding or subject
        if (params?.usubjid) {
          const sNode = data.nodes.find((n) => n.id === `SUBJ-${params.usubjid}`)
          const fNode = data.nodes.find((n) => n.type === 'finding' && n.data?.usubjid === params.usubjid)
          setSelectedNode(fNode || sNode || data.nodes[0] || null)
        } else if (data.nodes.length > 0) {
          const hysNode = data.nodes.find((n) => n.label === 'HYS_LAW')
          setSelectedNode(hysNode || data.nodes[0])
        }
      } catch (err: any) {
        setError(err.message || 'Failed to load knowledge graph.')
      } finally {
        setLoading(false)
      }
    },
    []
  )

  // Initial load: Hy's Law candidate 042-S05-003 preset
  useEffect(() => {
    loadGraph({ usubjid: '042-S05-003' })
  }, [loadGraph])

  // Presets handler
  const handleSelectPreset = (presetKey: string) => {
    setActivePreset(presetKey)
    setSearchQuery('')
    if (presetKey === 'hys-003') {
      loadGraph({ usubjid: '042-S05-003' })
    } else if (presetKey === 's07-001') {
      loadGraph({ usubjid: '042-S07-001' })
    } else if (presetKey === 's08-014') {
      loadGraph({ usubjid: '042-S08-014' })
    } else if (presetKey === 'overview') {
      loadGraph({})
    } else if (presetKey === 'sae') {
      loadGraph({ finding_id: 'SERIOUS_AE' })
    }
  }

  // Handle Search Submission
  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const q = searchQuery.trim()
    if (!q) return
    setActivePreset('custom')
    if (q.startsWith('042-') || allSubjects.includes(q)) {
      loadGraph({ usubjid: q })
    } else if (q.toUpperCase().includes('FIND') || q.toUpperCase().includes('HYS') || q.toUpperCase().includes('DOSE')) {
      loadGraph({ finding_id: q })
    } else if (q.includes(':') || q.toUpperCase().startsWith('LB') || q.toUpperCase().startsWith('AE')) {
      loadGraph({ record_ref: q })
    } else {
      loadGraph({ usubjid: q })
    }
  }

  // Tiered Layout calculation
  const nodePositions = useMemo(() => {
    if (!graphData) return {}
    const pos: Record<string, { x: number; y: number }> = { ...customPositions }

    const columns: Record<string, GraphNode[]> = {
      protocol: [],
      finding: [],
      escalation: [],
      evidence: [],
      record: [],
      subject: [],
      visit: [],
      other: [],
    }

    graphData.nodes.forEach((n) => {
      if (pos[n.id]) return
      if (n.type === 'study' || n.type === 'protocol') columns.protocol.push(n)
      else if (n.type === 'finding') columns.finding.push(n)
      else if (n.type === 'escalation' || n.type === 'query') columns.escalation.push(n)
      else if (n.type === 'evidence') columns.evidence.push(n)
      else if (n.type === 'lab' || n.type === 'adverse_event' || n.type === 'exposure' || n.type === 'clinical_record')
        columns.record.push(n)
      else if (n.type === 'subject') columns.subject.push(n)
      else if (n.type === 'visit') columns.visit.push(n)
      else columns.other.push(n)
    })

    const colX: Record<string, number> = {
      protocol: 120,
      finding: 420,
      escalation: 420,
      evidence: 720,
      record: 1020,
      subject: 1320,
      visit: 1560,
      other: 800,
    }

    Object.entries(columns).forEach(([colKey, nodes]) => {
      if (nodes.length === 0) return
      const baseX = colX[colKey] || 500
      const totalH = Math.max(500, nodes.length * 120)
      const startY = 120

      nodes.forEach((n, idx) => {
        if (!pos[n.id]) {
          const spacing = Math.max(110, totalH / (nodes.length + 1))
          const offsetY = colKey === 'escalation' ? 240 : 0
          pos[n.id] = {
            x: baseX,
            y: startY + idx * spacing + offsetY,
          }
        }
      })
    })

    return pos
  }, [graphData, customPositions])

  // Filter nodes according to typeFilter
  const visibleNodes = useMemo(() => {
    if (!graphData) return []
    if (typeFilter === 'all') return graphData.nodes
    return graphData.nodes.filter((n) => {
      if (typeFilter === 'subject') return n.type === 'subject'
      if (typeFilter === 'finding') return n.type === 'finding'
      if (typeFilter === 'evidence') return n.type === 'evidence'
      if (typeFilter === 'lab') return n.type === 'lab'
      if (typeFilter === 'adverse_event') return n.type === 'adverse_event'
      if (typeFilter === 'exposure') return n.type === 'exposure'
      if (typeFilter === 'protocol') return n.type === 'protocol' || n.type === 'study'
      if (typeFilter === 'visit') return n.type === 'visit'
      return true
    })
  }, [graphData, typeFilter])

  const visibleNodeIds = useMemo(() => new Set(visibleNodes.map((n) => n.id)), [visibleNodes])

  const visibleEdges = useMemo(() => {
    if (!graphData) return []
    return graphData.edges.filter((e) => visibleNodeIds.has(e.source) && visibleNodeIds.has(e.target))
  }, [graphData, visibleNodeIds])

  // Map of connected edges and nodes for hover highlight
  const connectedMap = useMemo(() => {
    const map: Record<string, Set<string>> = {}
    if (!graphData) return map
    graphData.edges.forEach((e) => {
      if (!map[e.source]) map[e.source] = new Set()
      if (!map[e.target]) map[e.target] = new Set()
      map[e.source].add(e.target)
      map[e.target].add(e.source)
    })
    return map
  }, [graphData])

  // Trace to Source logic: finds bidirectional causal path for selected node
  const handleTraceToSource = (startNode: GraphNode) => {
    if (!graphData) return
    const visited = new Set<string>()
    const queue = [startNode.id]
    visited.add(startNode.id)

    while (queue.length > 0) {
      const curr = queue.shift()!
      graphData.edges.forEach((e) => {
        if (e.source === curr && !visited.has(e.target)) {
          visited.add(e.target)
          queue.push(e.target)
        } else if (e.target === curr && !visited.has(e.source)) {
          visited.add(e.source)
          queue.push(e.source)
        }
      })
    }

    setTracedNodeIds(visited)
  }

  // Pan & Zoom handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).tagName === 'svg' || (e.target as HTMLElement).tagName === 'rect') {
      setIsPanning(true)
      setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y })
    }
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isPanning) {
      setPan({ x: e.clientX - panStart.x, y: e.clientY - panStart.y })
    } else if (draggingNodeId) {
      const newX = (e.clientX - pan.x) / zoom - dragOffset.x
      const newY = (e.clientY - pan.y) / zoom - dragOffset.y
      setCustomPositions((prev) => ({
        ...prev,
        [draggingNodeId]: { x: newX, y: newY },
      }))
    }
  }

  const handleMouseUp = () => {
    setIsPanning(false)
    setDraggingNodeId(null)
  }

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault()
    const delta = e.deltaY > 0 ? -0.08 : 0.08
    setZoom((prev) => Math.min(2.0, Math.max(0.3, prev + delta)))
  }

  const handleFitToScreen = () => {
    setZoom(0.85)
    setPan({ x: 60, y: 40 })
  }

  const handleResetView = () => {
    setZoom(0.9)
    setPan({ x: 80, y: 50 })
    setTracedNodeIds(new Set())
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100vh - 150px)',
        backgroundColor: '#070d18',
        borderRadius: '16px',
        border: '1px solid rgba(56, 189, 248, 0.15)',
        overflow: 'hidden',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
        position: 'relative',
      }}
    >
      {/* Top Header & Metrics Bar */}
      <div
        style={{
          padding: '0.85rem 1.25rem',
          background: 'rgba(10, 16, 30, 0.92)',
          borderBottom: '1px solid rgba(56, 189, 248, 0.12)',
          backdropFilter: 'blur(16px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '1rem',
          zIndex: 20,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div
            style={{
              width: '34px',
              height: '34px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #0284c7 0%, #6366f1 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 2px 10px rgba(14, 165, 233, 0.4)',
            }}
          >
            <Share2 size={18} color="#ffffff" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
                ATLAS Clinical Knowledge Graph
              </h2>
              <span className="badge badge-cyan" style={{ fontSize: '0.7rem' }}>
                PS2 MONITOR Grounding
              </span>
            </div>
            <div style={{ fontSize: '0.74rem', color: '#94a3b8' }}>
              Longitudinal Cross-Domain Provenance: Subject ➔ Records ➔ Evidence RecordRefs ➔ Findings ➔ Protocol Rules
            </div>
          </div>
        </div>

        {/* Study Grounding Stats Badges */}
        {graphData && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
            <div
              style={{
                padding: '0.35rem 0.65rem',
                borderRadius: '8px',
                background: 'rgba(15, 23, 42, 0.8)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                fontSize: '0.75rem',
                color: '#94a3b8',
              }}
            >
              Study Nodes:{' '}
              <strong style={{ color: '#38bdf8' }}>
                {graphData.stats.total_study_nodes.toLocaleString()}
              </strong>
            </div>
            <div
              style={{
                padding: '0.35rem 0.65rem',
                borderRadius: '8px',
                background: 'rgba(15, 23, 42, 0.8)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                fontSize: '0.75rem',
                color: '#94a3b8',
              }}
            >
              Records:{' '}
              <strong style={{ color: '#a855f7' }}>
                {graphData.stats.total_records.toLocaleString()}
              </strong>
            </div>
            <div
              style={{
                padding: '0.35rem 0.65rem',
                borderRadius: '8px',
                background: 'rgba(15, 23, 42, 0.8)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                fontSize: '0.75rem',
                color: '#94a3b8',
              }}
            >
              Subjects: <strong style={{ color: '#0ea5e9' }}>{graphData.stats.total_subjects}</strong>
            </div>
            <div
              style={{
                padding: '0.35rem 0.65rem',
                borderRadius: '8px',
                background: 'rgba(14, 165, 233, 0.1)',
                border: '1px solid rgba(14, 165, 233, 0.3)',
                fontSize: '0.75rem',
                color: '#38bdf8',
              }}
            >
              Active View: <strong>{visibleNodes.length} nodes</strong> /{' '}
              <strong>{visibleEdges.length} edges</strong>
            </div>
          </div>
        )}
      </div>

      {/* Control Bar: Search & Quick Presets & Filters */}
      <div
        style={{
          padding: '0.65rem 1.25rem',
          background: 'rgba(15, 23, 42, 0.75)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '0.75rem',
          zIndex: 15,
        }}
      >
        {/* Search Bar */}
        <form onSubmit={handleSearchSubmit} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              background: 'rgba(10, 16, 30, 0.85)',
              border: '1px solid rgba(56, 189, 248, 0.25)',
              borderRadius: '8px',
              padding: '0.4rem 0.75rem',
              width: '260px',
            }}
          >
            <Search size={14} color="#64748b" />
            <input
              type="text"
              placeholder="Search USUBJID, Finding, LB:31..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#f8fafc',
                fontSize: '0.8rem',
                outline: 'none',
                width: '100%',
              }}
            />
          </div>
          <button
            type="submit"
            style={{
              padding: '0.42rem 0.85rem',
              borderRadius: '8px',
              border: '1px solid rgba(56, 189, 248, 0.4)',
              background: 'linear-gradient(135deg, #0284c7 0%, #2563eb 100%)',
              color: '#ffffff',
              fontSize: '0.78rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Load
          </button>
        </form>

        {/* Quick Grounded Example Presets */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.74rem', color: '#64748b', marginRight: '0.2rem' }}>
            <Sparkles size={12} style={{ display: 'inline', marginRight: '3px' }} />
            Grounded Examples:
          </span>

          <button
            onClick={() => handleSelectPreset('hys-003')}
            style={{
              padding: '0.35rem 0.65rem',
              borderRadius: '6px',
              fontSize: '0.75rem',
              fontWeight: 600,
              cursor: 'pointer',
              border:
                activePreset === 'hys-003'
                  ? '1px solid #f59e0b'
                  : '1px solid rgba(245, 158, 11, 0.3)',
              background:
                activePreset === 'hys-003'
                  ? 'rgba(245, 158, 11, 0.25)'
                  : 'rgba(245, 158, 11, 0.08)',
              color: '#fbbf24',
            }}
          >
            ⭐ Hy's Law (042-S05-003)
          </button>

          <button
            onClick={() => handleSelectPreset('s07-001')}
            style={{
              padding: '0.35rem 0.65rem',
              borderRadius: '6px',
              fontSize: '0.75rem',
              fontWeight: 500,
              cursor: 'pointer',
              border:
                activePreset === 's07-001'
                  ? '1px solid #0ea5e9'
                  : '1px solid rgba(14, 165, 233, 0.25)',
              background:
                activePreset === 's07-001'
                  ? 'rgba(14, 165, 233, 0.25)'
                  : 'rgba(14, 165, 233, 0.08)',
              color: '#38bdf8',
            }}
          >
            S07 Unit Conv (042-S07-001)
          </button>

          <button
            onClick={() => handleSelectPreset('s08-014')}
            style={{
              padding: '0.35rem 0.65rem',
              borderRadius: '6px',
              fontSize: '0.75rem',
              fontWeight: 500,
              cursor: 'pointer',
              border:
                activePreset === 's08-014'
                  ? '1px solid #a855f7'
                  : '1px solid rgba(168, 85, 247, 0.25)',
              background:
                activePreset === 's08-014'
                  ? 'rgba(168, 85, 247, 0.25)'
                  : 'rgba(168, 85, 247, 0.08)',
              color: '#c084fc',
            }}
          >
            042-S08-014
          </button>

          <button
            onClick={() => handleSelectPreset('overview')}
            style={{
              padding: '0.35rem 0.65rem',
              borderRadius: '6px',
              fontSize: '0.75rem',
              fontWeight: 500,
              cursor: 'pointer',
              border:
                activePreset === 'overview'
                  ? '1px solid #38bdf8'
                  : '1px solid rgba(255, 255, 255, 0.1)',
              background:
                activePreset === 'overview'
                  ? 'rgba(56, 189, 248, 0.2)'
                  : 'rgba(255, 255, 255, 0.04)',
              color: '#e2e8f0',
            }}
          >
            Study Overview
          </button>

          <button
            onClick={() => handleSelectPreset('sae')}
            style={{
              padding: '0.35rem 0.65rem',
              borderRadius: '6px',
              fontSize: '0.75rem',
              fontWeight: 500,
              cursor: 'pointer',
              border:
                activePreset === 'sae'
                  ? '1px solid #f43f5e'
                  : '1px solid rgba(244, 63, 94, 0.25)',
              background:
                activePreset === 'sae'
                  ? 'rgba(244, 63, 94, 0.25)'
                  : 'rgba(244, 63, 94, 0.08)',
              color: '#fb7185',
            }}
          >
            SAE Surveillance
          </button>
        </div>

        {/* Viewport Toolbar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <button
            onClick={() => setZoom((z) => Math.min(2.0, z + 0.15))}
            title="Zoom In"
            style={{
              padding: '0.4rem',
              borderRadius: '6px',
              background: 'rgba(255, 255, 255, 0.06)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              color: '#94a3b8',
              cursor: 'pointer',
            }}
          >
            <ZoomIn size={14} />
          </button>
          <button
            onClick={() => setZoom((z) => Math.max(0.3, z - 0.15))}
            title="Zoom Out"
            style={{
              padding: '0.4rem',
              borderRadius: '6px',
              background: 'rgba(255, 255, 255, 0.06)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              color: '#94a3b8',
              cursor: 'pointer',
            }}
          >
            <ZoomOut size={14} />
          </button>
          <button
            onClick={handleFitToScreen}
            title="Fit to Screen"
            style={{
              padding: '0.4rem',
              borderRadius: '6px',
              background: 'rgba(255, 255, 255, 0.06)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              color: '#94a3b8',
              cursor: 'pointer',
            }}
          >
            <Maximize2 size={14} />
          </button>
          <button
            onClick={handleResetView}
            title="Reset View"
            style={{
              padding: '0.4rem',
              borderRadius: '6px',
              background: 'rgba(255, 255, 255, 0.06)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              color: '#94a3b8',
              cursor: 'pointer',
            }}
          >
            <RotateCcw size={14} />
          </button>
        </div>
      </div>

      {/* Node Type Filter Bar */}
      <div
        style={{
          padding: '0.4rem 1.25rem',
          background: 'rgba(10, 16, 30, 0.65)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          overflowX: 'auto',
          fontSize: '0.72rem',
          zIndex: 10,
        }}
      >
        <span style={{ color: '#64748b', display: 'flex', alignItems: 'center', gap: '3px' }}>
          <Filter size={11} /> Layer Filter:
        </span>
        {[
          { id: 'all', label: 'All Entities' },
          { id: 'subject', label: 'Subjects' },
          { id: 'finding', label: 'Findings' },
          { id: 'evidence', label: 'RecordRefs' },
          { id: 'lab', label: 'Labs (LB)' },
          { id: 'adverse_event', label: 'Adverse Events (AE)' },
          { id: 'protocol', label: 'Protocol Rules' },
          { id: 'visit', label: 'Visits' },
        ].map((f) => {
          const isAct = typeFilter === f.id
          return (
            <button
              key={f.id}
              onClick={() => setTypeFilter(f.id)}
              style={{
                padding: '0.2rem 0.55rem',
                borderRadius: '4px',
                border: isAct ? '1px solid #38bdf8' : '1px solid transparent',
                background: isAct ? 'rgba(56, 189, 248, 0.18)' : 'rgba(255, 255, 255, 0.04)',
                color: isAct ? '#38bdf8' : '#94a3b8',
                cursor: 'pointer',
                whiteSpace: 'nowrap',
              }}
            >
              {f.label}
            </button>
          )
        })}
      </div>

      {/* Main Canvas & Slide-out Panel Container */}
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        {/* Loading Overlay */}
        {loading && (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              background: 'rgba(7, 13, 24, 0.8)',
              backdropFilter: 'blur(8px)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '1rem',
              zIndex: 30,
            }}
          >
            <div className="spinner" />
            <div style={{ color: '#38bdf8', fontSize: '0.9rem', fontWeight: 600 }}>
              Traversing StudyGraph Longitudinal Neighborhood...
            </div>
          </div>
        )}

        {/* Error Overlay */}
        {error && (
          <div
            style={{
              position: 'absolute',
              top: '1rem',
              left: '50%',
              transform: 'translateX(-50%)',
              background: 'rgba(244, 63, 94, 0.2)',
              border: '1px solid #f43f5e',
              borderRadius: '8px',
              padding: '0.75rem 1.5rem',
              color: '#f8fafc',
              zIndex: 35,
              fontSize: '0.85rem',
            }}
          >
            {error}
          </div>
        )}

        {/* Interactive SVG Canvas */}
        <svg
          ref={svgRef}
          width="100%"
          height="100%"
          style={{ cursor: isPanning ? 'grabbing' : draggingNodeId ? 'grabbing' : 'grab', userSelect: 'none' }}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onWheel={handleWheel}
        >
          {/* Subtle Grid Pattern Background */}
          <defs>
            <pattern id="kg-grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255, 255, 255, 0.03)" strokeWidth="1" />
            </pattern>
            {/* Arrowhead marker for edges */}
            <marker id="arrow" viewBox="0 -5 10 10" refX="28" refY="0" markerWidth="6" markerHeight="6" orient="auto">
              <path d="M0,-4L8,0L0,4" fill="rgba(56, 189, 248, 0.6)" />
            </marker>
            <marker id="arrow-traced" viewBox="0 -5 10 10" refX="28" refY="0" markerWidth="7" markerHeight="7" orient="auto">
              <path d="M0,-4L8,0L0,4" fill="#fbbf24" />
            </marker>
          </defs>

          <rect width="100%" height="100%" fill="url(#kg-grid)" />

          {/* Transformed Content Group */}
          <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
            {/* Render Edges */}
            {visibleEdges.map((edge) => {
              const srcPos = nodePositions[edge.source]
              const tgtPos = nodePositions[edge.target]
              if (!srcPos || !tgtPos) return null

              const isConnectedToHover =
                hoveredNodeId && (edge.source === hoveredNodeId || edge.target === hoveredNodeId)
              const isTraced = tracedNodeIds.has(edge.source) && tracedNodeIds.has(edge.target)
              const isDimmed =
                (hoveredNodeId && !isConnectedToHover) || (tracedNodeIds.size > 0 && !isTraced)

              // Curve path
              const dx = tgtPos.x - srcPos.x
              const cx1 = srcPos.x + dx * 0.5
              const cy1 = srcPos.y
              const cx2 = srcPos.x + dx * 0.5
              const cy2 = tgtPos.y
              const pathD = `M ${srcPos.x} ${srcPos.y} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${tgtPos.x} ${tgtPos.y}`

              const midX = (srcPos.x + tgtPos.x) / 2
              const midY = (srcPos.y + tgtPos.y) / 2

              const strokeColor = isTraced
                ? '#fbbf24'
                : isConnectedToHover
                ? '#38bdf8'
                : 'rgba(56, 189, 248, 0.25)'

              const strokeW = isTraced ? 2.5 : isConnectedToHover ? 2 : 1.2

              return (
                <g key={edge.id} opacity={isDimmed ? 0.15 : 1} style={{ transition: 'opacity 0.2s ease' }}>
                  <path
                    d={pathD}
                    fill="none"
                    stroke={strokeColor}
                    strokeWidth={strokeW}
                    strokeDasharray={edge.type === 'EVALUATED_AGAINST' ? '4 3' : 'none'}
                    markerEnd={isTraced ? 'url(#arrow-traced)' : 'url(#arrow)'}
                  />
                  {/* Relationship Label */}
                  <rect
                    x={midX - 35}
                    y={midY - 9}
                    width="70"
                    height="18"
                    rx="4"
                    fill="rgba(7, 13, 24, 0.85)"
                    stroke={isTraced ? 'rgba(251, 191, 36, 0.4)' : 'rgba(255, 255, 255, 0.06)'}
                    strokeWidth="1"
                  />
                  <text
                    x={midX}
                    y={midY + 3.5}
                    fill={isTraced ? '#fbbf24' : isConnectedToHover ? '#38bdf8' : '#64748b'}
                    fontSize="8.5px"
                    fontWeight={isTraced ? 700 : 500}
                    textAnchor="middle"
                  >
                    {edge.label}
                  </text>
                </g>
              )
            })}

            {/* Render Nodes */}
            {visibleNodes.map((node) => {
              const pos = nodePositions[node.id]
              if (!pos) return null

              const cfg = NODE_CONFIG[node.type] || NODE_CONFIG.clinical_record
              const isSelected = selectedNode?.id === node.id
              const isHovered = hoveredNodeId === node.id
              const isNeighbor = hoveredNodeId && connectedMap[hoveredNodeId]?.has(node.id)
              const isTraced = tracedNodeIds.has(node.id)
              const isDimmed =
                (hoveredNodeId && !isHovered && !isNeighbor) || (tracedNodeIds.size > 0 && !isTraced)

              // Card dimensions
              const width = 175
              const height = 62
              const rx = 10

              return (
                <g
                  key={node.id}
                  transform={`translate(${pos.x - width / 2}, ${pos.y - height / 2})`}
                  opacity={isDimmed ? 0.2 : 1}
                  style={{
                    cursor: 'pointer',
                    transition: draggingNodeId === node.id ? 'none' : 'opacity 0.2s ease, transform 0.1s ease',
                  }}
                  onMouseEnter={() => setHoveredNodeId(node.id)}
                  onMouseLeave={() => setHoveredNodeId(null)}
                  onClick={(e) => {
                    e.stopPropagation()
                    setSelectedNode(node)
                  }}
                  onMouseDown={(e) => {
                    e.stopPropagation()
                    setDraggingNodeId(node.id)
                    setDragOffset({
                      x: (e.clientX - pan.x) / zoom - pos.x,
                      y: (e.clientY - pan.y) / zoom - pos.y,
                    })
                  }}
                >
                  {/* Glow halo when selected, hovered, or traced */}
                  {(isSelected || isHovered || isTraced) && (
                    <rect
                      x={-4}
                      y={-4}
                      width={width + 8}
                      height={height + 8}
                      rx={rx + 3}
                      fill="none"
                      stroke={isTraced ? '#fbbf24' : isSelected ? '#38bdf8' : cfg.color}
                      strokeWidth={isTraced || isSelected ? 2.5 : 1.5}
                      strokeOpacity={0.8}
                    />
                  )}

                  {/* Main Node Card Background */}
                  <rect
                    width={width}
                    height={height}
                    rx={rx}
                    fill={
                      isSelected
                        ? 'rgba(14, 165, 233, 0.2)'
                        : isTraced
                        ? 'rgba(251, 191, 36, 0.16)'
                        : 'rgba(15, 23, 42, 0.94)'
                    }
                    stroke={
                      isTraced
                        ? '#fbbf24'
                        : isSelected
                        ? '#38bdf8'
                        : isHovered
                        ? cfg.color
                        : cfg.border
                    }
                    strokeWidth={isSelected || isTraced ? 1.8 : 1.2}
                  />

                  {/* Left accent color bar */}
                  <rect x={0} y={0} width={5} height={height} rx={2} fill={cfg.color} />

                  {/* Node Type Badge Text */}
                  <text x={14} y={16} fill={cfg.color} fontSize="9px" fontWeight={700} letterSpacing="0.04em">
                    {cfg.label.toUpperCase()}
                  </text>

                  {/* Primary Node Label */}
                  <text
                    x={14}
                    y={34}
                    fill="#f8fafc"
                    fontSize="11.5px"
                    fontWeight={600}
                    style={{ whiteSpace: 'nowrap' }}
                  >
                    {node.label.length > 20 ? `${node.label.slice(0, 19)}…` : node.label}
                  </text>

                  {/* Sublabel / Metric */}
                  <text x={14} y={49} fill="#94a3b8" fontSize="9.5px">
                    {node.sublabel.length > 24 ? `${node.sublabel.slice(0, 23)}…` : node.sublabel}
                  </text>
                </g>
              )
            })}
          </g>
        </svg>

        {/* Floating Canvas Legend */}
        <div
          style={{
            position: 'absolute',
            bottom: '1rem',
            left: '1rem',
            background: 'rgba(10, 16, 30, 0.88)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '10px',
            padding: '0.65rem 0.9rem',
            backdropFilter: 'blur(16px)',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.4rem',
            fontSize: '0.72rem',
            zIndex: 10,
            maxWidth: '280px',
          }}
        >
          <div style={{ fontWeight: 600, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Layers size={13} color="#38bdf8" /> Grounding Legend & Flow
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.35rem 0.75rem' }}>
            {Object.entries(NODE_CONFIG).slice(0, 8).map(([key, cfg]) => (
              <div key={key} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span
                  style={{
                    width: '9px',
                    height: '9px',
                    borderRadius: '50%',
                    backgroundColor: cfg.color,
                    display: 'inline-block',
                  }}
                />
                <span style={{ color: '#cbd5e1' }}>{cfg.label}</span>
              </div>
            ))}
          </div>
          <div
            style={{
              marginTop: '0.3rem',
              borderTop: '1px solid rgba(255, 255, 255, 0.06)',
              paddingTop: '0.3rem',
              fontSize: '0.68rem',
              color: '#64748b',
            }}
          >
            Drag nodes to rearrange. Click to inspect underlying domain CSV rows.
          </div>
        </div>

        {/* Slide-out Node Details Panel */}
        {selectedNode && (
          <div
            style={{
              position: 'absolute',
              top: '1rem',
              right: '1rem',
              bottom: '1rem',
              width: '380px',
              background: 'rgba(10, 16, 30, 0.95)',
              border: '1px solid rgba(56, 189, 248, 0.25)',
              borderRadius: '14px',
              backdropFilter: 'blur(24px)',
              boxShadow: '-8px 12px 36px rgba(0, 0, 0, 0.6)',
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
              zIndex: 25,
            }}
          >
            {/* Panel Header */}
            <div
              style={{
                padding: '1rem 1.25rem',
                borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
                background: 'rgba(15, 23, 42, 0.6)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <div
                  style={{
                    width: '28px',
                    height: '28px',
                    borderRadius: '6px',
                    background: (NODE_CONFIG[selectedNode.type] || NODE_CONFIG.clinical_record).bg,
                    border: `1px solid ${(NODE_CONFIG[selectedNode.type] || NODE_CONFIG.clinical_record).border}`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {(NODE_CONFIG[selectedNode.type] || NODE_CONFIG.clinical_record).icon}
                </div>
                <div>
                  <div style={{ fontSize: '0.72rem', color: (NODE_CONFIG[selectedNode.type] || NODE_CONFIG.clinical_record).color, fontWeight: 700 }}>
                    {(NODE_CONFIG[selectedNode.type] || NODE_CONFIG.clinical_record).label.toUpperCase()}
                  </div>
                  <div style={{ fontSize: '1rem', fontWeight: 700, color: '#f8fafc' }}>
                    {selectedNode.label}
                  </div>
                </div>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#94a3b8',
                  fontSize: '1.2rem',
                  cursor: 'pointer',
                  padding: '0.2rem 0.5rem',
                }}
              >
                ✕
              </button>
            </div>

            {/* Panel Body Content */}
            <div style={{ flex: 1, padding: '1.25rem', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '1.1rem' }}>
              {/* Primary Trace Action */}
              <div
                style={{
                  background: 'rgba(14, 165, 233, 0.08)',
                  border: '1px solid rgba(14, 165, 233, 0.25)',
                  borderRadius: '10px',
                  padding: '0.85rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <div>
                  <div style={{ fontSize: '0.82rem', fontWeight: 600, color: '#38bdf8' }}>
                    Bidirectional Traceability
                  </div>
                  <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
                    Highlight full evidence & protocol causal chain
                  </div>
                </div>
                <button
                  onClick={() => handleTraceToSource(selectedNode)}
                  style={{
                    padding: '0.4rem 0.8rem',
                    borderRadius: '6px',
                    border: '1px solid #fbbf24',
                    background: 'rgba(251, 191, 36, 0.2)',
                    color: '#fbbf24',
                    fontSize: '0.76rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                >
                  <Sparkles size={13} /> Trace Source
                </button>
              </div>

              {/* Node Specific Details */}
              {selectedNode.type === 'subject' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#f8fafc' }}>Subject Demographics</div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                    <div className="card" style={{ padding: '0.6rem' }}>
                      <div style={{ fontSize: '0.68rem', color: '#64748b' }}>USUBJID</div>
                      <div style={{ fontSize: '0.85rem', color: '#38bdf8', fontWeight: 600 }}>{selectedNode.data.usubjid}</div>
                    </div>
                    <div className="card" style={{ padding: '0.6rem' }}>
                      <div style={{ fontSize: '0.68rem', color: '#64748b' }}>SITE ID</div>
                      <div style={{ fontSize: '0.85rem', color: '#f8fafc', fontWeight: 600 }}>Site {selectedNode.data.site}</div>
                    </div>
                    <div className="card" style={{ padding: '0.6rem' }}>
                      <div style={{ fontSize: '0.68rem', color: '#64748b' }}>AGE / SEX</div>
                      <div style={{ fontSize: '0.85rem', color: '#f8fafc', fontWeight: 600 }}>
                        {selectedNode.data.age} years / {selectedNode.data.sex}
                      </div>
                    </div>
                    <div className="card" style={{ padding: '0.6rem' }}>
                      <div style={{ fontSize: '0.68rem', color: '#64748b' }}>TREATMENT ARM</div>
                      <div style={{ fontSize: '0.85rem', color: '#10b981', fontWeight: 600 }}>{selectedNode.data.arm}</div>
                    </div>
                  </div>

                  {/* Connected Record Breakdown */}
                  {selectedNode.data.record_counts && (
                    <div>
                      <div style={{ fontSize: '0.78rem', color: '#94a3b8', marginBottom: '0.4rem', fontWeight: 600 }}>
                        StudyGraph Record Counts:
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                        {Object.entries(selectedNode.data.record_counts).map(([dom, cnt]: any) => (
                          <span key={dom} className="badge badge-indigo" style={{ fontSize: '0.72rem' }}>
                            {dom}: {cnt}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {selectedNode.type === 'finding' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#f8fafc' }}>Finding Details</div>
                    <span
                      className={`badge ${
                        selectedNode.data.severity === 'CRITICAL'
                          ? 'badge-rose'
                          : selectedNode.data.severity === 'HIGH'
                          ? 'badge-amber'
                          : 'badge-cyan'
                      }`}
                    >
                      {selectedNode.data.severity}
                    </span>
                  </div>

                  <div className="card" style={{ padding: '0.75rem' }}>
                    <div style={{ fontSize: '0.7rem', color: '#64748b' }}>FINDING ID</div>
                    <div style={{ fontSize: '0.85rem', color: '#fbbf24', fontWeight: 600, fontFamily: 'monospace' }}>
                      {selectedNode.data.finding_id}
                    </div>
                  </div>

                  <div className="card" style={{ padding: '0.75rem' }}>
                    <div style={{ fontSize: '0.7rem', color: '#64748b' }}>CLINICAL RATIONALE</div>
                    <div style={{ fontSize: '0.82rem', color: '#f8fafc', marginTop: '0.2rem', lineHeight: 1.4 }}>
                      {selectedNode.data.rationale || selectedNode.data.description}
                    </div>
                  </div>

                  {/* Supporting Evidence RecordRefs */}
                  {selectedNode.data.evidence && selectedNode.data.evidence.length > 0 && (
                    <div>
                      <div style={{ fontSize: '0.78rem', color: '#94a3b8', marginBottom: '0.4rem', fontWeight: 600 }}>
                        Supporting Evidence RecordRefs:
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                        {selectedNode.data.evidence.map((ev: any, idx: number) => (
                          <div
                            key={idx}
                            style={{
                              padding: '0.5rem 0.75rem',
                              borderRadius: '6px',
                              background: 'rgba(251, 191, 36, 0.1)',
                              border: '1px solid rgba(251, 191, 36, 0.3)',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              fontSize: '0.78rem',
                            }}
                          >
                            <span style={{ color: '#fbbf24', fontWeight: 600 }}>
                              {ev.domain} Sequence #{ev.seq}
                            </span>
                            <span style={{ color: '#94a3b8', fontFamily: 'monospace' }}>
                              {ev.usubjid || selectedNode.data.usubjid}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {(selectedNode.type === 'lab' || selectedNode.type === 'adverse_event' || selectedNode.type === 'exposure') && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#f8fafc' }}>
                    Underlying Clinical Observation
                  </div>

                  <div className="card" style={{ padding: '0.75rem' }}>
                    <div style={{ fontSize: '0.7rem', color: '#64748b' }}>SOURCE RECORD CITATION</div>
                    <div style={{ fontSize: '0.9rem', color: '#38bdf8', fontWeight: 700, fontFamily: 'monospace' }}>
                      RecordRef {selectedNode.data.domain || (selectedNode.type === 'lab' ? 'LB' : selectedNode.type === 'adverse_event' ? 'AE' : 'EX')}:
                      {selectedNode.data.SEQ || selectedNode.data.LBSEQ || selectedNode.data.AESEQ || selectedNode.data.EXSEQ}
                    </div>
                  </div>

                  {selectedNode.type === 'lab' && (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                      <div className="card" style={{ padding: '0.6rem' }}>
                        <div style={{ fontSize: '0.68rem', color: '#64748b' }}>LAB TEST</div>
                        <div style={{ fontSize: '0.85rem', color: '#a855f7', fontWeight: 600 }}>
                          {selectedNode.data.LBTESTCD} ({selectedNode.data.LBTEST || selectedNode.data.LBTESTCD})
                        </div>
                      </div>
                      <div className="card" style={{ padding: '0.6rem' }}>
                        <div style={{ fontSize: '0.68rem', color: '#64748b' }}>STANDARDIZED VALUE</div>
                        <div style={{ fontSize: '0.85rem', color: '#fbbf24', fontWeight: 700 }}>
                          {selectedNode.data.LB_STD_VAL} {selectedNode.data.LB_STD_UNIT}
                        </div>
                      </div>
                      <div className="card" style={{ padding: '0.6rem' }}>
                        <div style={{ fontSize: '0.68rem', color: '#64748b' }}>RAW RESULT / UNIT</div>
                        <div style={{ fontSize: '0.82rem', color: '#94a3b8' }}>
                          {selectedNode.data.LBORRES} {selectedNode.data.LBORRESU}
                        </div>
                      </div>
                      <div className="card" style={{ padding: '0.6rem' }}>
                        <div style={{ fontSize: '0.68rem', color: '#64748b' }}>VISIT / DATE</div>
                        <div style={{ fontSize: '0.82rem', color: '#38bdf8' }}>
                          {selectedNode.data.VISIT} ({selectedNode.data.LBDTC})
                        </div>
                      </div>
                    </div>
                  )}

                  {selectedNode.type === 'adverse_event' && (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                      <div className="card" style={{ padding: '0.6rem' }}>
                        <div style={{ fontSize: '0.68rem', color: '#64748b' }}>AE TERM</div>
                        <div style={{ fontSize: '0.85rem', color: '#f43f5e', fontWeight: 600 }}>
                          {selectedNode.data.AETERM}
                        </div>
                      </div>
                      <div className="card" style={{ padding: '0.6rem' }}>
                        <div style={{ fontSize: '0.68rem', color: '#64748b' }}>SEVERITY</div>
                        <div style={{ fontSize: '0.85rem', color: '#fb7185', fontWeight: 600 }}>
                          {selectedNode.data.AESEV}
                        </div>
                      </div>
                      <div className="card" style={{ padding: '0.6rem' }}>
                        <div style={{ fontSize: '0.68rem', color: '#64748b' }}>SERIOUS (AESER)</div>
                        <div style={{ fontSize: '0.85rem', color: selectedNode.data.AESER === 'Y' ? '#ef4444' : '#94a3b8', fontWeight: 600 }}>
                          {selectedNode.data.AESER || 'N'}
                        </div>
                      </div>
                      <div className="card" style={{ padding: '0.6rem' }}>
                        <div style={{ fontSize: '0.68rem', color: '#64748b' }}>HOSPITALIZATION</div>
                        <div style={{ fontSize: '0.85rem', color: selectedNode.data.AESHOSP === 'Y' ? '#ef4444' : '#94a3b8', fontWeight: 600 }}>
                          {selectedNode.data.AESHOSP || 'N'}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {selectedNode.type === 'protocol' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#f8fafc' }}>Protocol Specification</div>
                  <div className="card" style={{ padding: '0.75rem' }}>
                    <div style={{ fontSize: '0.7rem', color: '#64748b' }}>SECTION / TITLE</div>
                    <div style={{ fontSize: '0.85rem', color: '#38bdf8', fontWeight: 600 }}>
                      {selectedNode.data.title || selectedNode.label}
                    </div>
                  </div>
                  <div className="card" style={{ padding: '0.75rem' }}>
                    <div style={{ fontSize: '0.7rem', color: '#64748b' }}>CRITERIA & THRESHOLDS</div>
                    <div style={{ fontSize: '0.8rem', color: '#f8fafc', marginTop: '0.2rem', lineHeight: 1.4 }}>
                      {selectedNode.data.criteria}
                    </div>
                  </div>
                  {selectedNode.data.action && (
                    <div className="card" style={{ padding: '0.75rem' }}>
                      <div style={{ fontSize: '0.7rem', color: '#64748b' }}>MANDATED MONITOR ACTION</div>
                      <div style={{ fontSize: '0.8rem', color: '#fbbf24', marginTop: '0.2rem' }}>
                        {selectedNode.data.action}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {selectedNode.type === 'escalation' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#f8fafc' }}>
                    Medical Review Action
                  </div>
                  <div className="card" style={{ padding: '0.75rem' }}>
                    <div style={{ fontSize: '0.7rem', color: '#64748b' }}>ESCALATION ID</div>
                    <div style={{ fontSize: '0.85rem', color: '#ec4899', fontWeight: 600, fontFamily: 'monospace' }}>
                      {selectedNode.data.escalation_id}
                    </div>
                  </div>
                  <div className="card" style={{ padding: '0.75rem' }}>
                    <div style={{ fontSize: '0.7rem', color: '#64748b' }}>REASON & SUMMARY</div>
                    <div style={{ fontSize: '0.82rem', color: '#f8fafc', marginTop: '0.2rem' }}>
                      {selectedNode.data.summary || selectedNode.data.reason}
                    </div>
                  </div>
                </div>
              )}

              {/* Raw JSON Inspector for Judges */}
              <div style={{ marginTop: '0.5rem' }}>
                <div style={{ fontSize: '0.72rem', color: '#64748b', marginBottom: '0.35rem', fontWeight: 600 }}>
                  RAW RECORD GRAPH DATA (GROUNDED VERIFICATION):
                </div>
                <pre
                  style={{
                    background: 'rgba(0, 0, 0, 0.45)',
                    border: '1px solid rgba(255, 255, 255, 0.06)',
                    borderRadius: '8px',
                    padding: '0.65rem',
                    fontSize: '0.68rem',
                    color: '#94a3b8',
                    overflowX: 'auto',
                    maxHeight: '180px',
                  }}
                >
                  {JSON.stringify(selectedNode.data, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
