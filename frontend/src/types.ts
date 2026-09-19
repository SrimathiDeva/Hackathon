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

// =============================================================================
// STAGE 2 — PROBLEM STATEMENT 2 (MONITOR) TYPES
// =============================================================================

export interface Stage2RecordRef {
  domain: string;
  usubjid?: string;
  seq?: number;
  document?: string;
  section?: string;
  details?: Record<string, any>;
}

export interface Stage2Finding {
  finding_id: string;
  usubjid: string;
  site_id: string;
  cut: number;
  category: string;
  code: string;
  severity: string;
  description: string;
  evidence: Stage2RecordRef[];
}

export interface Stage2HumanDecision {
  decision: 'APPROVED' | 'REJECTED' | 'CLARIFY' | string;
  user: string;
  timestamp: string;
  reason?: string;
  downgraded_to?: string;
  transmitted_action?: Record<string, any>;
}

export interface Stage2Clarification {
  question: string;
  answer: string;
  evidence: Stage2RecordRef[];
}

export interface Stage2Escalation {
  escalation_id: string;
  finding_id: string;
  usubjid: string;
  site_id: string;
  code: string;
  severity: string;
  summary: string;
  rationale: string;
  evidence: Stage2RecordRef[];
  status: 'PENDING_HUMAN_REVIEW' | 'APPROVED' | 'REJECTED' | 'RESUBMITTED' | string;
  human_decision?: Stage2HumanDecision;
  clarification?: Stage2Clarification;
}

export interface Stage2Query {
  query_id: string;
  finding_id: string;
  usubjid: string;
  site_id: string;
  domain: string;
  target_field: string;
  query_text: string;
  severity: string;
  status: 'OPEN' | 'RESOLVED' | string;
  evidence: Stage2RecordRef[];
}

export interface Stage2Deviation {
  deviation_id: string;
  usubjid: string;
  site_id: string;
  protocol_version: number;
  category: string;
  description: string;
  severity: string;
  evidence: Stage2RecordRef[];
}

export interface Stage2TraceEntry {
  trace_id?: string;
  timestamp: string;
  node: 'detect' | 'medical_review' | 'data_manager' | 'compliance' | 'human_gate' | 'execute' | string;
  action?: string;
  decision: string;
  subject?: string;
  finding_id?: string;
  evidence?: any[];
  details?: Record<string, any>;
  metadata?: Record<string, any>;
}

export interface Stage2TraceSummary {
  total_decisions?: number;
  nodes_active?: string[];
  decisions_per_node?: Record<string, number>;
  latest_timestamp?: string | null;
  [key: string]: any;
}

export interface Stage2Report {
  cycle_id: string;
  cut: number;
  protocol_version: number;
  timestamp: string;
  status: string;
  summary: {
    total_findings: number;
    total_escalations: number;
    total_queries: number;
    total_deviations: number;
    total_actions_executed: number;
    total_trace_entries: number;
  };
  breakdowns: {
    findings: Record<string, number>;
    escalations: Record<string, number>;
    deviations: Record<string, number>;
    query_domains: Record<string, number>;
  };
  findings: Stage2Finding[];
  escalations: Stage2Escalation[];
  queries: Stage2Query[];
  deviations: Stage2Deviation[];
  actions_executed: Array<Record<string, any>>;
  trace_entries: Stage2TraceEntry[];
  trace_summary: Stage2TraceSummary;
  memory_stats: {
    stored_queries: number;
    stored_escalations: number;
    stored_deviations: number;
    human_decisions: number;
  };
}

export interface Stage2DuplicateTestResult {
  cut: number;
  protocol_version: number;
  cycle_1: {
    findings: number;
    escalations: number;
    queries: number;
    deviations: number;
  };
  cycle_2: {
    findings: number;
    escalations: number;
    queries: number;
    deviations: number;
  };
  suppressed: {
    escalations: number;
    queries: number;
    deviations: number;
    total: number;
  };
  suppression_rate_percent: number;
  persisted_in_memory: {
    escalations: number;
    queries: number;
    deviations: number;
  };
}

export interface ProtocolVersionBreakdown {
  version: number;
  label: string;
  rules: string;
  total_deviations: number;
  breakdown: Record<string, number>;
}

export interface Stage2ProtocolComparison {
  cut: number;
  versions: ProtocolVersionBreakdown[];
  amendment_highlights: string[];
}

export type GraphNodeType =
  | 'subject'
  | 'clinical_record'
  | 'lab'
  | 'adverse_event'
  | 'exposure'
  | 'visit'
  | 'protocol'
  | 'finding'
  | 'evidence'
  | 'escalation'
  | 'query'
  | 'study';

export interface GraphNode {
  id: string;
  type: GraphNodeType;
  label: string;
  sublabel: string;
  data: Record<string, any>;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  label: string;
}

export interface KnowledgeGraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  stats: {
    total_study_nodes: number;
    total_study_edges: number;
    total_subjects: number;
    total_records: number;
    active_cut: number;
    protocol_version: number;
    findings_in_cycle: number;
    escalations_in_cycle: number;
    deviations_in_cycle: number;
    returned_nodes: number;
    returned_edges: number;
  };
  query: {
    usubjid?: string | null;
    finding_id?: string | null;
    record_ref?: string | null;
    node_type?: string | null;
    cut?: number;
    protocol_version?: number;
  };
}


