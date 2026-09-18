import type {
  StudyStats,
  AtlasAnswer,
  PublicQuestionItem,
  ProtocolInfo,
  HysLawData,
  Patient360Data,
} from './types'

// Use relative /api if Vite proxy is running, or explicit port 8000
const API_BASE = ''

export async function fetchHealth(): Promise<{ status: string; service: string }> {
  const res = await fetch(`${API_BASE}/api/health`)
  if (!res.ok) throw new Error('Backend unavailable')
  return res.json()
}

export async function fetchStats(): Promise<StudyStats> {
  const res = await fetch(`${API_BASE}/api/stats`)
  if (!res.ok) throw new Error('Failed to fetch stats')
  return res.json()
}

export async function fetchPatientsList(): Promise<{ total: number; subjects: string[] }> {
  const res = await fetch(`${API_BASE}/api/patients`)
  if (!res.ok) throw new Error('Failed to fetch patients')
  return res.json()
}

export async function fetchPatient360(usubjid: string): Promise<Patient360Data> {
  const res = await fetch(`${API_BASE}/api/patient/${encodeURIComponent(usubjid.trim())}`)
  if (res.status === 404) {
    throw new Error(`Subject not found: No Patient 360 record is available for '${usubjid}'.`)
  }
  if (!res.ok) {
    throw new Error(`Error fetching patient data: ${res.statusText}`)
  }
  return res.json()
}

export async function askAtlas(question: string, kind?: string): Promise<AtlasAnswer> {
  const res = await fetch(`${API_BASE}/api/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, kind }),
  })
  if (!res.ok) {
    throw new Error('ATLAS engine error analyzing clinical question')
  }
  return res.json()
}

export async function fetchPublicQuestions(): Promise<PublicQuestionItem[]> {
  const res = await fetch(`${API_BASE}/api/public-questions`)
  if (!res.ok) throw new Error('Failed to load public questions')
  return res.json()
}

export async function fetchProtocol(): Promise<ProtocolInfo> {
  const res = await fetch(`${API_BASE}/api/protocol`)
  if (!res.ok) throw new Error('Failed to load protocol data')
  return res.json()
}

export async function fetchHysLaw(): Promise<HysLawData> {
  const res = await fetch(`${API_BASE}/api/hys-law`)
  if (!res.ok) throw new Error('Failed to load Hy\'s Law findings')
  return res.json()
}
