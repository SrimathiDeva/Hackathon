export interface StudyStats {
  nodes: number;
  edges: number;
  subjects: number;
  clinical_records: number;
  cuts: number;
  corrections: number;
  build_time_ms: number;
}

export interface RecordRefDetails {
  test?: string;
  test_name?: string;
  raw_value?: string;
  raw_unit?: string;
  value?: number | null;
  unit?: string;
  date?: string;
  visit?: string;
  converted?: boolean;
  term?: string;
  severity?: string;
  start_date?: string;
  end_date?: string;
  outcome?: string;
  dose?: string;
  age?: string;
  sex?: string;
  arm?: string;
  country?: string;
  site?: string;
  treatment?: string;
}

export interface RecordRef {
  domain: string;
  usubjid?: string;
  seq?: number;
  document?: string;
  section?: string;
  details?: RecordRefDetails;
}

export interface AtlasAnswer {
  question_id: string;
  answer: any;
  text: string;
  evidence: RecordRef[];
  confidence: number;
  steps_used: number;
  tokens_used: number;
}

export interface PublicQuestionItem {
  question_id: string;
  text: string;
  kind: string;
  answer: any;
  explanation: string;
  confidence: number;
  evidence_count: number;
  evidence_sample: any[];
}

export interface ProtocolTimelineItem {
  phase: string;
  cuts: string;
  window: string;
  description: string;
}

export interface ProtocolCutDetail {
  cut: number;
  version: number;
  window: string;
  corrections: number;
}

export interface ProtocolInfo {
  timeline: ProtocolTimelineItem[];
  cuts_count: number;
  corrections_count: number;
  current_cut: number | null;
  details: ProtocolCutDetail[];
}

export interface HysLawCandidate {
  usubjid: string;
  site: string;
  demographics: Record<string, any>;
  alt_records: Array<{
    seq: number;
    visit: string;
    date: string;
    raw_val: string;
    raw_unit: string;
    std_val: number;
    std_unit: string;
    converted?: boolean;
  }>;
  bili_records: Array<{
    seq: number;
    visit: string;
    date: string;
    raw_val: string;
    raw_unit: string;
    std_val: number;
    std_unit: string;
  }>;
  is_s07_special: boolean;
  evidence_count: number;
}

export interface HysLawData {
  rule: string;
  uln_limits: Record<string, string>;
  s07_conversion: string;
  candidates: string[];
  details: HysLawCandidate[];
}

export interface Patient360Data {
  usubjid: string;
  site_id: string;
  demographics: Record<string, any>;
  adverse_events: Record<string, any>[];
  labs: Record<string, any>[];
  vitals: Record<string, any>[];
  exposure: Record<string, any>[];
  medications: Record<string, any>[];
  disposition: Record<string, any> | null;
  history: Record<string, any>[];
  ecg: Record<string, any>[];
}

export interface QueryPlanStage {
  step: number;
  name: string;
  status: 'COMPLETED' | 'SKIPPED' | 'FAILED' | string;
  description: string;
  details?: Record<string, any>;
}

export interface QueryExplanation {
  interpreted_intent?: string;
  operation?: string;
  extracted_entities?: Record<string, any>;
  selected_protocol_cut?: string;
  domains_used?: string[];
  execution_steps?: number;
  result_count?: number;
  evidence_count?: number;
  validation_status?: string;
  details?: string;
}

export interface ProvenanceLineageNode {
  node: string;
  label: string;
  detail: string;
}

export interface ProvenanceRecord {
  subject?: string;
  domain?: string;
  record_ref?: RecordRef;
  lineage: ProvenanceLineageNode[];
}

export interface QueryValidationBlock {
  status: 'PASS' | 'FAIL' | string;
  total_evidence: number;
  verified_evidence: number;
  unsupported_fabrication_count: number;
  audit_compliant: boolean;
}

export interface QueryResponse {
  question: string;
  parsed_query: Record<string, any>;
  query_plan: QueryPlanStage[];
  explanation: QueryExplanation;
  answer: any;
  text?: string;
  evidence: RecordRef[];
  provenance: ProvenanceRecord[];
  validation: QueryValidationBlock;
  elapsed_ms?: number;
}

