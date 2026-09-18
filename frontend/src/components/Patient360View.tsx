import React, { useState, useEffect } from 'react'
import { Search } from 'lucide-react'
import { fetchPatient360, fetchPatientsList } from '../api'
import type { Patient360Data } from '../types'

interface Patient360ViewProps {
  initialSubject?: string
}

export const Patient360View: React.FC<Patient360ViewProps> = ({ initialSubject = '042-S07-001' }) => {
  const [searchQuery, setSearchQuery] = useState(initialSubject)
  const [currentPatient, setCurrentPatient] = useState<Patient360Data | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeDomainTab, setActiveDomainTab] = useState<string>('labs')
  const [allSubjects, setAllSubjects] = useState<string[]>([])

  useEffect(() => {
    fetchPatientsList()
      .then((data) => setAllSubjects(data.subjects))
      .catch(() => {})
  }, [])

  const loadPatient = async (usubjid: string) => {
    if (!usubjid.trim()) return
    setLoading(true)
    setError(null)
    try {
      const data = await fetchPatient360(usubjid.trim())
      setCurrentPatient(data)
    } catch (err: any) {
      setError(err.message || 'Error loading Patient 360')
      setCurrentPatient(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadPatient(initialSubject)
  }, [initialSubject])

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    loadPatient(searchQuery)
  }

  const sampleSubjects = ['042-S07-001', '042-S05-003', '042-S08-014', '042-S01-003', '042-S02-013']

  // Compile chronological timeline events from available domain records with dates
  const timelineEvents: Array<{ domain: string; date: string; title: string; detail: string }> = []
  if (currentPatient) {
    // Demographics / enrollment
    if (currentPatient.demographics.RFSTDTC) {
      timelineEvents.push({
        domain: 'DM',
        date: currentPatient.demographics.RFSTDTC,
        title: 'Study Enrollment',
        detail: `Subject enrolled into arm ${currentPatient.demographics.ARM || 'UNKNOWN'}`,
      })
    }
    // Dosing
    for (const ex of currentPatient.exposure || []) {
      const dt = ex.EXSTDTC_PARSED || ex.EXSTDTC
      if (dt) {
        timelineEvents.push({
          domain: 'EX',
          date: String(dt),
          title: `Dose Administered: ${ex.EXDOSE || ''} ${ex.EXDOSU || ''}`,
          detail: `Visit: ${ex.VISIT || 'N/A'} | Dose: ${ex.EXDOSE || ''} ${ex.EXDOSU || ''}`,
        })
      }
    }
    // Adverse events
    for (const ae of currentPatient.adverse_events || []) {
      const dt = ae.AESTDTC_PARSED || ae.AESTDTC
      if (dt) {
        timelineEvents.push({
          domain: 'AE',
          date: String(dt),
          title: `Adverse Event: ${ae.AETERM || 'AE'}`,
          detail: `Severity: ${ae.AESEV || 'N/A'} | Outcome: ${ae.AEOUT || 'N/A'}`,
        })
      }
    }
    // Distinct laboratory visits
    const seenLabVisits = new Set<string>()
    for (const lb of currentPatient.labs || []) {
      const dt = lb.LBDTC_PARSED || lb.LBDTC
      const visit = lb.VISIT || 'Visit'
      if (dt && !seenLabVisits.has(`${dt}_${visit}`)) {
        seenLabVisits.add(`${dt}_${visit}`)
        timelineEvents.push({
          domain: 'LB',
          date: String(dt),
          title: `Laboratory Panel (${visit})`,
          detail: `Collected at ${visit}`,
        })
      }
    }
    // Sort timeline chronologically
    timelineEvents.sort((a, b) => (a.date > b.date ? 1 : -1))
  }

  const domainTabs = [
    { id: 'demographics', label: 'Demographics', count: currentPatient?.demographics ? 1 : 0 },
    { id: 'labs', label: 'Laboratory', count: currentPatient?.labs?.length || 0 },
    { id: 'vitals', label: 'Vital Signs', count: currentPatient?.vitals?.length || 0 },
    { id: 'ae', label: 'Adverse Events', count: currentPatient?.adverse_events?.length || 0 },
    { id: 'exposure', label: 'Dosing', count: currentPatient?.exposure?.length || 0 },
    { id: 'meds', label: 'Medications', count: currentPatient?.medications?.length || 0 },
    { id: 'history', label: 'Medical History', count: currentPatient?.history?.length || 0 },
    { id: 'disposition', label: 'Disposition', count: currentPatient?.disposition ? 1 : 0 },
    { id: 'timeline', label: 'Timeline', count: timelineEvents.length },
  ]

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      {/* Search Header */}
      <div>
        <h1 style={{ fontSize: '2rem', fontWeight: 800, color: '#f8fafc', marginBottom: '0.4rem' }}>
          Patient 360
        </h1>
        <p style={{ color: '#94a3b8', fontSize: '0.95rem' }}>
          Longitudinal subject exploration synthesizing clinical records across all 9 domains into a unified record ({allSubjects.length} subjects indexed).
        </p>

        {/* Search Bar */}
        <form onSubmit={handleSearchSubmit} style={{ marginTop: '1.25rem', display: 'flex', gap: '0.75rem' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <input
              type="text"
              className="input-field"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search USUBJID (e.g. 042-S07-001)"
              style={{ paddingLeft: '2.75rem' }}
              list="subjects-list"
            />
            <datalist id="subjects-list">
              {allSubjects.map((s) => (
                <option key={s} value={s} />
              ))}
            </datalist>
            <Search
              size={18}
              color="#64748b"
              style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)' }}
            />
          </div>
          <button type="submit" className="btn-primary">
            Search Patient
          </button>
        </form>

        {/* Quick Suggestion Chips */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.75rem', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Quick Candidates:</span>
          {sampleSubjects.map((s) => (
            <button
              key={s}
              onClick={() => {
                setSearchQuery(s)
                loadPatient(s)
              }}
              className="badge badge-cyan font-mono"
              style={{ cursor: 'pointer', background: searchQuery === s ? 'rgba(14, 165, 233, 0.3)' : undefined }}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Loading & Error States */}
      {loading && (
        <div className="glass-card" style={{ padding: '3rem', textAlign: 'center' }}>
          <div style={{ color: '#38bdf8', fontSize: '1rem', fontWeight: 600 }}>
            Querying Patient 360 graph structure...
          </div>
        </div>
      )}

      {error && (
        <div
          className="glass-card"
          style={{
            padding: '1.75rem',
            borderLeft: '4px solid #f43f5e',
            background: 'rgba(244, 63, 94, 0.08)',
          }}
        >
          <div style={{ color: '#f8fafc', fontWeight: 700, fontSize: '1.1rem', marginBottom: '0.25rem' }}>
            Subject not found
          </div>
          <div style={{ color: '#fda4af', fontSize: '0.9rem' }}>
            {error}
          </div>
        </div>
      )}

      {/* Patient Data Cards */}
      {currentPatient && !loading && (
        <>
          {/* Patient Overview Card */}
          <div className="glass-card" style={{ padding: '1.75rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                  <h2 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#f8fafc', fontFamily: 'var(--font-mono)' }}>
                    {currentPatient.usubjid}
                  </h2>
                  <span className="badge badge-cyan">Site {currentPatient.site_id}</span>
                  {currentPatient.site_id === 'S07' && (
                    <span className="badge badge-amber">µkat/L Unit Site</span>
                  )}
                </div>
                <div style={{ color: '#94a3b8', fontSize: '0.85rem', marginTop: '0.35rem' }}>
                  Assigned Treatment Arm:{' '}
                  <strong style={{ color: '#38bdf8' }}>
                    {currentPatient.demographics.ARM || 'UNKNOWN'}
                  </strong>
                </div>
              </div>

              {/* Demographic Pills */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', background: 'rgba(10, 16, 30, 0.6)', padding: '0.75rem 1.25rem', borderRadius: '10px' }}>
                <div>
                  <div style={{ fontSize: '0.7rem', color: '#64748b', textTransform: 'uppercase' }}>Age / Sex</div>
                  <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: '0.9rem' }}>
                    {currentPatient.demographics.AGE || 'N/A'} yrs / {currentPatient.demographics.SEX || 'N/A'}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '0.7rem', color: '#64748b', textTransform: 'uppercase' }}>Country</div>
                  <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: '0.9rem' }}>
                    {currentPatient.demographics.COUNTRY || 'N/A'}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '0.7rem', color: '#64748b', textTransform: 'uppercase' }}>Initials / Birth</div>
                  <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: '0.9rem' }}>
                    {currentPatient.demographics.INITS || 'N/A'} ({currentPatient.demographics.BRTHDTC || 'N/A'})
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Domain Tabs */}
          <div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', borderBottom: '1px solid rgba(56, 189, 248, 0.12)', paddingBottom: '0.5rem' }}>
              {domainTabs.map((t) => {
                const isActive = activeDomainTab === t.id
                return (
                  <button
                    key={t.id}
                    onClick={() => setActiveDomainTab(t.id)}
                    style={{
                      background: isActive ? 'rgba(14, 165, 233, 0.15)' : 'transparent',
                      color: isActive ? '#38bdf8' : '#94a3b8',
                      border: isActive ? '1px solid rgba(56, 189, 248, 0.3)' : '1px solid transparent',
                      padding: '0.5rem 0.85rem',
                      borderRadius: '8px',
                      fontSize: '0.85rem',
                      fontWeight: isActive ? 600 : 500,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.4rem',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    {t.label}
                    <span
                      style={{
                        fontSize: '0.7rem',
                        padding: '0.1rem 0.4rem',
                        borderRadius: '9999px',
                        background: isActive ? 'rgba(56, 189, 248, 0.3)' : 'rgba(255, 255, 255, 0.08)',
                        color: isActive ? '#f8fafc' : '#64748b',
                      }}
                    >
                      {t.count}
                    </span>
                  </button>
                )
              })}
            </div>

            {/* Tab Contents */}
            <div style={{ marginTop: '1.25rem' }}>
              {/* Laboratory Tab */}
              {activeDomainTab === 'labs' && (
                <div className="glass-card" style={{ padding: '1.5rem', overflowX: 'auto' }}>
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem', color: '#f8fafc' }}>
                    Laboratory Findings ({currentPatient.labs.length} records)
                  </h3>
                  {currentPatient.labs.length === 0 ? (
                    <div style={{ color: '#64748b', fontStyle: 'italic' }}>No laboratory records found for this subject.</div>
                  ) : (
                    <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.88rem' }}>
                      <thead>
                        <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)', color: '#94a3b8' }}>
                          <th style={{ padding: '0.6rem' }}>Seq</th>
                          <th style={{ padding: '0.6rem' }}>Test</th>
                          <th style={{ padding: '0.6rem' }}>Raw Result</th>
                          <th style={{ padding: '0.6rem' }}>Standard Result</th>
                          <th style={{ padding: '0.6rem' }}>Visit</th>
                          <th style={{ padding: '0.6rem' }}>Date</th>
                          <th style={{ padding: '0.6rem' }}>Conversion</th>
                        </tr>
                      </thead>
                      <tbody>
                        {currentPatient.labs.map((lb, idx) => (
                          <tr key={idx} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                            <td style={{ padding: '0.6rem', fontFamily: 'var(--font-mono)', color: '#64748b' }}>{lb.LBSEQ}</td>
                            <td style={{ padding: '0.6rem', fontWeight: 600, color: '#f8fafc' }}>{lb.LBTESTCD}</td>
                            <td style={{ padding: '0.6rem', color: '#cbd5e1' }}>
                              {lb.LBORRES} {lb.LBORRESU}
                            </td>
                            <td style={{ padding: '0.6rem', color: '#38bdf8', fontWeight: 600 }}>
                              {lb.LB_STD_VAL !== null && lb.LB_STD_VAL !== undefined ? `${lb.LB_STD_VAL} ${lb.LB_STD_UNIT}` : 'None'}
                            </td>
                            <td style={{ padding: '0.6rem', color: '#94a3b8' }}>{lb.VISIT}</td>
                            <td style={{ padding: '0.6rem', color: '#94a3b8', fontFamily: 'var(--font-mono)' }}>
                              {lb.LBDTC_PARSED || lb.LBDTC}
                            </td>
                            <td style={{ padding: '0.6rem' }}>
                              {lb.LB_CONVERTED ? (
                                <span className="badge badge-amber" style={{ fontSize: '0.68rem' }}>
                                  60x µkat/L → U/L
                                </span>
                              ) : (
                                <span style={{ color: '#64748b', fontSize: '0.75rem' }}>Direct</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              )}

              {/* Vital Signs Tab */}
              {activeDomainTab === 'vitals' && (
                <div className="glass-card" style={{ padding: '1.5rem', overflowX: 'auto' }}>
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem', color: '#f8fafc' }}>
                    Vital Signs ({currentPatient.vitals.length} records)
                  </h3>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.88rem' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)', color: '#94a3b8' }}>
                        <th style={{ padding: '0.6rem' }}>Seq</th>
                        <th style={{ padding: '0.6rem' }}>Test</th>
                        <th style={{ padding: '0.6rem' }}>Result</th>
                        <th style={{ padding: '0.6rem' }}>Visit</th>
                        <th style={{ padding: '0.6rem' }}>Date</th>
                      </tr>
                    </thead>
                    <tbody>
                      {currentPatient.vitals.map((vs, idx) => (
                        <tr key={idx} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                          <td style={{ padding: '0.6rem', fontFamily: 'var(--font-mono)', color: '#64748b' }}>{vs.VSSEQ}</td>
                          <td style={{ padding: '0.6rem', fontWeight: 600, color: '#f8fafc' }}>{vs.VSTESTCD}</td>
                          <td style={{ padding: '0.6rem', color: '#38bdf8' }}>{vs.VSORRES} {vs.VSORRESU}</td>
                          <td style={{ padding: '0.6rem', color: '#94a3b8' }}>{vs.VISIT}</td>
                          <td style={{ padding: '0.6rem', color: '#94a3b8', fontFamily: 'var(--font-mono)' }}>{vs.VSDTC}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Adverse Events Tab */}
              {activeDomainTab === 'ae' && (
                <div className="glass-card" style={{ padding: '1.5rem' }}>
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem', color: '#f8fafc' }}>
                    Adverse Events ({currentPatient.adverse_events.length} records)
                  </h3>
                  {currentPatient.adverse_events.length === 0 ? (
                    <div style={{ color: '#34d399', fontSize: '0.9rem' }}>No adverse events recorded for this subject.</div>
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
                      {currentPatient.adverse_events.map((ae, idx) => (
                        <div key={idx} style={{ background: 'rgba(10, 16, 30, 0.7)', padding: '1rem', borderRadius: '10px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
                          <div style={{ fontWeight: 700, color: '#f8fafc', fontSize: '1rem', marginBottom: '0.4rem' }}>
                            {ae.AETERM}
                          </div>
                          <div style={{ fontSize: '0.8rem', color: '#94a3b8', display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                            <div>Severity: <strong style={{ color: ae.AESEV === 'SEVERE' ? '#f43f5e' : '#fbbf24' }}>{ae.AESEV}</strong></div>
                            <div>Outcome: {ae.AEOUT || 'N/A'}</div>
                            <div>Start Date: <span className="font-mono">{ae.AESTDTC}</span></div>
                            <div>End Date: <span className="font-mono">{ae.AEENDTC || 'Ongoing'}</span></div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Dosing Tab */}
              {activeDomainTab === 'exposure' && (
                <div className="glass-card" style={{ padding: '1.5rem' }}>
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem', color: '#f8fafc' }}>
                    Dosing Administrations ({currentPatient.exposure.length} doses)
                  </h3>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '0.85rem' }}>
                    {currentPatient.exposure.map((ex, idx) => (
                      <div key={idx} style={{ background: 'rgba(10, 16, 30, 0.7)', padding: '0.85rem', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
                        <div style={{ fontWeight: 600, color: '#38bdf8', fontSize: '0.95rem' }}>
                          {ex.EXDOSE} {ex.EXDOSU}
                        </div>
                        <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '0.25rem' }}>
                          Visit: {ex.VISIT || 'N/A'}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#64748b', fontFamily: 'var(--font-mono)', marginTop: '0.2rem' }}>
                          {ex.EXSTDTC}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Medications Tab */}
              {activeDomainTab === 'meds' && (
                <div className="glass-card" style={{ padding: '1.5rem' }}>
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem', color: '#f8fafc' }}>
                    Concomitant Medications ({currentPatient.medications.length} records)
                  </h3>
                  {currentPatient.medications.length === 0 ? (
                    <div style={{ color: '#64748b', fontStyle: 'italic' }}>No concomitant medications reported.</div>
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '0.85rem' }}>
                      {currentPatient.medications.map((cm, idx) => (
                        <div key={idx} style={{ background: 'rgba(10, 16, 30, 0.7)', padding: '0.85rem', borderRadius: '8px' }}>
                          <div style={{ fontWeight: 600, color: '#f8fafc' }}>{cm.CMTRT}</div>
                          <div style={{ fontSize: '0.78rem', color: '#94a3b8', marginTop: '0.25rem' }}>
                            Indication: {cm.CMINDC || 'N/A'}
                          </div>
                          <div style={{ fontSize: '0.75rem', color: '#64748b', fontFamily: 'var(--font-mono)' }}>
                            {cm.CMSTDTC}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Demographics Raw Tab */}
              {activeDomainTab === 'demographics' && (
                <div className="glass-card" style={{ padding: '1.5rem' }}>
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem', color: '#f8fafc' }}>
                    Demographics Data (DM)
                  </h3>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
                    {Object.entries(currentPatient.demographics).map(([key, val]) => (
                      <div key={key} style={{ background: 'rgba(10, 16, 30, 0.6)', padding: '0.75rem', borderRadius: '8px' }}>
                        <div style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase' }}>{key}</div>
                        <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: '0.9rem', marginTop: '0.2rem' }}>
                          {String(val || 'None')}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Disposition Tab */}
              {activeDomainTab === 'disposition' && (
                <div className="glass-card" style={{ padding: '1.5rem' }}>
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem', color: '#f8fafc' }}>
                    Study Disposition (DS)
                  </h3>
                  {currentPatient.disposition ? (
                    <div style={{ background: 'rgba(10, 16, 30, 0.7)', padding: '1rem', borderRadius: '10px' }}>
                      {Object.entries(currentPatient.disposition).map(([k, v]) => (
                        <div key={k} style={{ marginBottom: '0.5rem', display: 'flex', gap: '1rem' }}>
                          <span style={{ color: '#64748b', minWidth: '120px' }}>{k}:</span>
                          <span style={{ color: '#f8fafc', fontWeight: 500 }}>{String(v)}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={{ color: '#34d399' }}>Subject completed study or has ongoing active participation.</div>
                  )}
                </div>
              )}

              {/* Medical History Tab */}
              {activeDomainTab === 'history' && (
                <div className="glass-card" style={{ padding: '1.5rem' }}>
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem', color: '#f8fafc' }}>
                    Medical History (MH) ({currentPatient.history.length} conditions)
                  </h3>
                  {currentPatient.history.length === 0 ? (
                    <div style={{ color: '#64748b', fontStyle: 'italic' }}>No prior medical history records.</div>
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '0.85rem' }}>
                      {currentPatient.history.map((mh, idx) => (
                        <div key={idx} style={{ background: 'rgba(10, 16, 30, 0.7)', padding: '0.85rem', borderRadius: '8px' }}>
                          <div style={{ fontWeight: 600, color: '#f8fafc' }}>{mh.MHTERM}</div>
                          <div style={{ fontSize: '0.75rem', color: '#64748b', fontFamily: 'var(--font-mono)', marginTop: '0.2rem' }}>
                            {mh.MHDTC || 'Prior condition'}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Timeline Tab */}
              {activeDomainTab === 'timeline' && (
                <div className="glass-card" style={{ padding: '2rem' }}>
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '1.5rem', color: '#f8fafc' }}>
                    Longitudinal Chronological Events
                  </h3>
                  {timelineEvents.length === 0 ? (
                    <div style={{ color: '#64748b' }}>No dated events available for this subject.</div>
                  ) : (
                    <div style={{ position: 'relative', paddingLeft: '2rem', borderLeft: '2px solid rgba(56, 189, 248, 0.3)' }}>
                      {timelineEvents.map((ev, idx) => (
                        <div key={idx} style={{ position: 'relative', marginBottom: '1.75rem' }}>
                          {/* Dot on line */}
                          <div
                            style={{
                              position: 'absolute',
                              left: '-2.45rem',
                              top: '0.25rem',
                              width: '12px',
                              height: '12px',
                              borderRadius: '50%',
                              backgroundColor: ev.domain === 'AE' ? '#f43f5e' : ev.domain === 'LB' ? '#38bdf8' : '#10b981',
                              boxShadow: '0 0 8px rgba(56, 189, 248, 0.4)',
                            }}
                          />
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.2rem' }}>
                            <span className="badge badge-cyan font-mono" style={{ fontSize: '0.72rem' }}>
                              {ev.date}
                            </span>
                            <span className="badge badge-indigo" style={{ fontSize: '0.7rem' }}>
                              {ev.domain}
                            </span>
                            <span style={{ fontWeight: 600, color: '#f8fafc', fontSize: '0.92rem' }}>
                              {ev.title}
                            </span>
                          </div>
                          <div style={{ color: '#94a3b8', fontSize: '0.82rem' }}>
                            {ev.detail}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
