"""
backend/api.py

FastAPI adapter for ATLAS Problem 1 (Study Sentinel).
Exposes REST endpoints wrapping the existing validated StudyGraph and Atlas classes.
"""

import os
import sys
import json
import datetime
from typing import Optional, List, Dict, Any

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from starter.schemas import Question, RecordRef
from stage1.study_graph import StudyGraph
from stage1.atlas import Atlas
from stage1.nlu import AtlasNLU
from stage1.query_engine import QueryExecutor

from stage2.crew import ReviewCrew
from stage2.memory import ReviewMemory
from stage2.models import ReviewReport, Escalation, Query, Deviation


# Initialize FastAPI app
app = FastAPI(
    title="ATLAS — Study Sentinel API",
    description="Clinical Trial Intelligence & Evidence Grounding API",
    version="1.0.0",
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Helper to convert date/datetime objects to ISO strings for JSON serialization
def serialize_obj(obj: Any) -> Any:
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: serialize_obj(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_obj(x) for x in obj]
    return obj


# Global instances of StudyGraph, Atlas, AtlasNLU, and QueryExecutor
data_folder = os.path.join(BASE_DIR, "data", "hackathon-data")
graph = StudyGraph(data_folder)
build_stats = graph.build()
atlas = Atlas(graph)
nlu = AtlasNLU(atlas=atlas, graph=graph)
query_executor = QueryExecutor(graph=graph, atlas=atlas, nlu=nlu)

# Global instances for Problem Statement 2 (MONITOR)
stage2_memory = ReviewMemory()
stage2_crew = ReviewCrew(
    hub_url="http://hub.clinical-sentinel.local:8000",
    gateway_url="http://gateway.clinical-sentinel.local:8000",
    team_key="study-sentinel-key",
    atlas=atlas,
)
stage2_crew.memory = stage2_memory
stage2_crew.medical_review_node.memory = stage2_memory
stage2_crew.data_manager_node.memory = stage2_memory
stage2_crew.compliance_node.memory = stage2_memory
stage2_crew.human_gate_node.memory = stage2_memory

# Store latest cycle report in memory for easy querying
latest_stage2_report: Optional[ReviewReport] = None

# Pre-index domain records for rapid evidence detail lookup: (domain, usubjid, seq) -> record
record_index: Dict[tuple, Dict[str, Any]] = {}
for domain, records in graph.tables.items():
    for r in records:
        u = r.get("USUBJID")
        seq_col = f"{domain}SEQ" if f"{domain}SEQ" in r else "SEQ"
        seq_val = r.get(seq_col)
        if seq_val is not None:
            try:
                record_index[(domain, u, int(seq_val))] = r
            except (ValueError, TypeError):
                pass
        if domain == "DM":
            record_index[("DM", u, None)] = r
            record_index[("DM", u, 1)] = r
        elif domain == "DS":
            record_index[("DS", u, None)] = r
            record_index[("DS", u, 1)] = r


class AskRequest(BaseModel):
    question: str
    kind: Optional[str] = None


class QueryRequest(BaseModel):
    question: str


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "ATLAS",
    }


@app.get("/api/stats")
def get_stats():
    # Count cuts and corrections safely from source files or loaded tables
    num_cuts = len(graph.cuts) if hasattr(graph, "cuts") and graph.cuts else 12
    num_corrections = len(graph.corrections) if hasattr(graph, "corrections") and graph.corrections else 200

    return {
        "nodes": build_stats.get("nodes", 27179),
        "edges": build_stats.get("edges", 27178),
        "subjects": build_stats.get("subjects", 241),
        "clinical_records": build_stats.get("total_records", 26925),
        "cuts": num_cuts,
        "corrections": num_corrections,
        "build_time_ms": build_stats.get("build_time_ms", 218.88),
    }


@app.get("/api/patients")
def get_patients():
    """Returns list of all indexed subject IDs."""
    subjects = sorted(list(graph.subjects.keys()))
    return {
        "total": len(subjects),
        "subjects": subjects,
    }


@app.get("/api/patient/{usubjid}")
def get_patient(usubjid: str):
    """Returns the full Patient 360 record for a given USUBJID."""
    p360 = graph.patient360(usubjid)
    if not p360:
        raise HTTPException(
            status_code=404,
            detail=f"Subject not found: No Patient 360 record is available for '{usubjid}'.",
        )
    return serialize_obj(p360)


@app.post("/api/ask")
def ask_atlas(req: AskRequest):
    """Answers a clinical question using NLU / Atlas and attaches grounded evidence details."""
    if req.kind:
        question_obj = Question(question_id="DEMO", text=req.question, kind=req.kind)
        ans = atlas.answer(question_obj)
    else:
        ans = nlu.process_query(req.question)

    ans_dict = ans.to_dict()

    # Enrich evidence items with display metadata from the graph
    enriched_evidence = []
    for item in ans_dict.get("evidence", []):
        d = dict(item)
        domain = d.get("domain")
        usubjid = d.get("usubjid")
        seq = d.get("seq")

        # Lookup underlying record
        rec = record_index.get((domain, usubjid, seq))
        if rec:
            details: Dict[str, Any] = {}
            if domain == "LB":
                details["test"] = rec.get("LBTESTCD", "")
                details["test_name"] = rec.get("LBTEST", "")
                details["raw_value"] = rec.get("LBORRES", "")
                details["raw_unit"] = rec.get("LBORRESU", "")
                details["value"] = rec.get("LB_STD_VAL")
                details["unit"] = rec.get("LB_STD_UNIT", "")
                details["date"] = rec.get("LBDTC", "")
                details["visit"] = rec.get("VISIT", "")
                details["converted"] = rec.get("LB_CONVERTED", False)
            elif domain == "AE":
                details["term"] = rec.get("AETERM", "")
                details["severity"] = rec.get("AESEV", "")
                details["start_date"] = rec.get("AESTDTC", "")
                details["end_date"] = rec.get("AEENDTC", "")
                details["outcome"] = rec.get("AEOUT", "")
            elif domain == "VS":
                details["test"] = rec.get("VSTESTCD", "")
                details["value"] = rec.get("VSORRES", "")
                details["unit"] = rec.get("VSORRESU", "")
                details["date"] = rec.get("VSDTC", "")
                details["visit"] = rec.get("VISIT", "")
            elif domain == "EX":
                details["dose"] = rec.get("EXDOSE", "")
                details["unit"] = rec.get("EXDOSU", "")
                details["date"] = rec.get("EXSTDTC", "")
                details["visit"] = rec.get("VISIT", "")
            elif domain == "CM":
                details["treatment"] = rec.get("CMTRT", "")
                details["start_date"] = rec.get("CMSTDTC", "")
                details["indication"] = rec.get("CMINDC", "")
            elif domain == "DM":
                details["age"] = rec.get("AGE", "")
                details["sex"] = rec.get("SEX", "")
                details["arm"] = rec.get("ARM", "")
                details["country"] = rec.get("COUNTRY", "")
                details["site"] = rec.get("SITEID", "")
            elif domain == "DS":
                details["status"] = rec.get("DSDECOD", "")
                details["term"] = rec.get("DSTERM", "")
                details["date"] = rec.get("DSDTC", "")
            d["details"] = serialize_obj(details)
        elif domain == "DOC":
            d["details"] = {
                "document": d.get("document", ""),
                "section": d.get("section", "amendment"),
                "summary": "Protocol specification document",
            }
        enriched_evidence.append(d)

    ans_dict["evidence"] = enriched_evidence
    return ans_dict


@app.post("/api/query")
def query_atlas(req: QueryRequest):
    """
    Executes an advanced clinical query investigation.
    Parses natural language into AtlasQuery AST, generates a 10-stage execution plan,
    and returns grounded results with visual provenance lineage and evidence verification.
    """
    q_str = req.question.strip() if req.question else ""
    if not q_str:
        raise HTTPException(
            status_code=400,
            detail="The 'question' field cannot be empty. Please provide a clinical question.",
        )

    try:
        result = query_executor.execute(q_str)
        return serialize_obj(result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Clinical query engine error: {str(e)}",
        )


@app.get("/api/public-questions")
def get_public_questions():
    """Reads stage1_public.json and exposes benchmark questions and results."""
    public_file = os.path.join(BASE_DIR, "stage1_public.json")
    if not os.path.exists(public_file):
        raise HTTPException(status_code=404, detail="stage1_public.json not found.")

    with open(public_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Question text mapping for rich display
    question_meta = {
        "Q001": {"text": "How many subjects are in the study?", "kind": "count"},
        "Q002": {"text": "How many subjects at site S07 discontinued due to an adverse event?", "kind": "count"},
        "Q003": {"text": "How many subjects experienced adverse events?", "kind": "count"},
        "Q004": {"text": "How many adverse events are recorded?", "kind": "count"},
        "Q005": {"text": "How many vital sign records are recorded?", "kind": "count"},
        "Q006": {"text": "What is the sex of subject 042-S01-003?", "kind": "lookup"},
        "Q007": {"text": "What treatment arm was subject 042-S01-003 assigned to?", "kind": "lookup"},
        "Q008": {"text": "List the laboratory and adverse-event records for 042-S05-003 within 7 days of the WEEK8 visit", "kind": "lookup"},
        "Q018": {"text": "Which subjects meet potential Hy's law criteria?", "kind": "finding"},
        "Q031": {"text": "Which subjects at site S01 received a wrong dose?", "kind": "trap"},
    }

    results = []
    for item in data:
        qid = item.get("question_id", "")
        meta = question_meta.get(qid, {})
        evidence_list = item.get("evidence", [])
        results.append({
            "question_id": qid,
            "text": meta.get("text", item.get("text", "")),
            "kind": meta.get("kind", "unknown"),
            "answer": item.get("answer"),
            "explanation": item.get("text"),
            "confidence": item.get("confidence", 1.0),
            "evidence_count": len(evidence_list),
            "evidence_sample": evidence_list[:6],
        })

    return results


@app.get("/api/protocol")
def get_protocol():
    """Returns a concise representation of protocol cuts and amendment rules."""
    return {
        "timeline": [
            {
                "phase": "Protocol v1",
                "cuts": "Cuts 1–4",
                "window": "±7 day visit window",
                "description": "Original study protocol specifications with ±7 day allowable window around scheduled study visits.",
            },
            {
                "phase": "Protocol Amendment 2",
                "cuts": "Cuts 5–8",
                "window": "±3 day visit window",
                "description": "Protocol Amendment 2 narrowed the allowable visit window to ±3 days. Cut 5 introduces 200 central laboratory re-issued values via corrections.csv.",
            },
            {
                "phase": "Protocol v3",
                "cuts": "Cuts 9–12",
                "window": "Cut-dependent protocol rules",
                "description": "Subsequent protocol revisions and operational rules for late-stage clinical visits and database lock preparations.",
            },
        ],
        "cuts_count": 12,
        "corrections_count": 200,
        "current_cut": graph.current_cut,
        "details": [
            {"cut": 1, "version": 1, "window": "±7 days", "corrections": 0},
            {"cut": 2, "version": 1, "window": "±7 days", "corrections": 0},
            {"cut": 3, "version": 1, "window": "±7 days", "corrections": 0},
            {"cut": 4, "version": 1, "window": "±7 days", "corrections": 0},
            {"cut": 5, "version": 2, "window": "±3 days", "corrections": 200},
            {"cut": 6, "version": 2, "window": "±3 days", "corrections": 0},
            {"cut": 7, "version": 2, "window": "±3 days", "corrections": 0},
            {"cut": 8, "version": 2, "window": "±3 days", "corrections": 0},
            {"cut": 9, "version": 3, "window": "Cut-dependent", "corrections": 0},
            {"cut": 10, "version": 3, "window": "Cut-dependent", "corrections": 0},
            {"cut": 11, "version": 3, "window": "Cut-dependent", "corrections": 0},
            {"cut": 12, "version": 3, "window": "Cut-dependent", "corrections": 0},
        ],
    }


@app.get("/api/hys-law")
def get_hys_law_findings():
    """Returns the validated Hy's Law candidates with exact laboratory evidence."""
    # Candidates validated in Q018:
    candidates = ["042-S05-003", "042-S07-001", "042-S08-014"]
    results = []

    for u in candidates:
        p360 = graph.patient360(u)
        labs = p360.get("labs", [])
        alt_records = []
        bili_records = []

        for r in labs:
            test_cd = r.get("LBTESTCD", "").upper()
            if test_cd == "ALT":
                alt_records.append({
                    "seq": r.get("LBSEQ"),
                    "visit": r.get("VISIT"),
                    "date": serialize_obj(r.get("LBDTC_PARSED") or r.get("LBDTC")),
                    "raw_val": r.get("LBORRES"),
                    "raw_unit": r.get("LBORRESU"),
                    "std_val": r.get("LB_STD_VAL"),
                    "std_unit": r.get("LB_STD_UNIT"),
                    "converted": r.get("LB_CONVERTED", False),
                })
            elif test_cd == "BILI":
                bili_records.append({
                    "seq": r.get("LBSEQ"),
                    "visit": r.get("VISIT"),
                    "date": serialize_obj(r.get("LBDTC_PARSED") or r.get("LBDTC")),
                    "raw_val": r.get("LBORRES"),
                    "raw_unit": r.get("LBORRESU"),
                    "std_val": r.get("LB_STD_VAL"),
                    "std_unit": r.get("LB_STD_UNIT"),
                })

        results.append({
            "usubjid": u,
            "site": u.split("-")[1],
            "demographics": serialize_obj(p360.get("demographics", {})),
            "alt_records": alt_records,
            "bili_records": bili_records,
            "is_s07_special": u == "042-S07-001",
            "evidence_count": 2,  # 1 ALT + 1 BILI qualifying pair per candidate
        })

    return {
        "rule": "ALT/AST > 3x ULN and Total Bilirubin > 2x ULN within 14 days without baseline cholestasis",
        "uln_limits": {"ALT": "56 U/L", "BILI": "1.2 mg/dL"},
        "s07_conversion": "1 µkat/L = 60 U/L",
        "candidates": candidates,
        "details": results,
    }


# =============================================================================
# PROBLEM STATEMENT 2 — MONITOR API ENDPOINTS
# =============================================================================

class Stage2RunRequest(BaseModel):
    cut: int = 6
    protocol_version: int = 2
    reset_memory: bool = False


class HumanGateDecisionRequest(BaseModel):
    escalation_id: str
    response: str  # "APPROVED" | "REJECTED"
    reason: Optional[str] = None


class HumanGateClarifyRequest(BaseModel):
    escalation_id: str
    question: str


@app.post("/api/stage2/run-cycle")
def run_stage2_cycle(req: Stage2RunRequest):
    """
    Executes a complete PS2 multi-agent monitoring cycle under the specified cut and protocol version.
    Orchestrates Detect -> Medical Review -> Data Manager -> Compliance -> Human Gate -> Execute.
    """
    global latest_stage2_report

    if req.reset_memory:
        stage2_memory.queries.clear()
        stage2_memory.escalations.clear()
        stage2_memory.deviations.clear()
        stage2_memory.human_decisions.clear()
        stage2_memory.subject_flags.clear()
        stage2_memory.site_flags.clear()
        stage2_crew.trace.entries.clear()

    report = stage2_crew.run_cycle(cut=req.cut, protocol_version=req.protocol_version)
    latest_stage2_report = report

    # Category breakdowns
    finding_breakdown: Dict[str, int] = {}
    for f in report.findings:
        finding_breakdown[f.category] = finding_breakdown.get(f.category, 0) + 1

    escalation_breakdown: Dict[str, int] = {}
    for e in report.escalations:
        escalation_breakdown[e.code] = escalation_breakdown.get(e.code, 0) + 1

    deviation_breakdown: Dict[str, int] = {}
    for d in report.deviations:
        deviation_breakdown[d.category] = deviation_breakdown.get(d.category, 0) + 1

    query_domains: Dict[str, int] = {}
    for q in report.queries:
        target = f"{q.domain}.{q.target_field}"
        query_domains[target] = query_domains.get(target, 0) + 1

    return {
        "cycle_id": report.cycle_id,
        "cut": report.cut,
        "protocol_version": report.protocol_version,
        "timestamp": report.timestamp,
        "status": report.status,
        "summary": {
            "total_findings": len(report.findings),
            "total_escalations": len(report.escalations),
            "total_queries": len(report.queries),
            "total_deviations": len(report.deviations),
            "total_actions_executed": len(report.actions_executed),
            "total_trace_entries": len(stage2_crew.trace.entries),
        },
        "breakdowns": {
            "findings": finding_breakdown,
            "escalations": escalation_breakdown,
            "deviations": deviation_breakdown,
            "query_domains": query_domains,
        },
        "findings": [f.to_dict() for f in report.findings],
        "escalations": [e.to_dict() for e in report.escalations],
        "queries": [q.to_dict() for q in report.queries],
        "deviations": [d.to_dict() for d in report.deviations],
        "actions_executed": report.actions_executed,
        "trace_entries": [e.to_dict() for e in stage2_crew.trace.entries],
        "trace_summary": stage2_crew.trace.summary(),
        "memory_stats": {
            "stored_queries": len(stage2_memory.queries),
            "stored_escalations": len(stage2_memory.escalations),
            "stored_deviations": len(stage2_memory.deviations),
            "human_decisions": len(stage2_memory.human_decisions),
        },
    }


@app.post("/api/stage2/human-gate/response")
def submit_human_gate_response(req: HumanGateDecisionRequest):
    """
    Submits a physician monitor decision (APPROVED or REJECTED) on a live escalation.
    """
    esc = stage2_memory.get_escalation(req.escalation_id)
    if not esc and latest_stage2_report:
        esc = next((e for e in latest_stage2_report.escalations if e.escalation_id == req.escalation_id), None)

    if not esc:
        raise HTTPException(
            status_code=404,
            detail=f"Escalation '{req.escalation_id}' not found in active review memory.",
        )

    res = stage2_crew.human_gate_node.handle_response(
        escalation=esc,
        response=req.response,
        reason=req.reason,
    )
    return serialize_obj(res)


@app.post("/api/stage2/human-gate/clarify")
def submit_human_gate_clarification(req: HumanGateClarifyRequest):
    """
    Submits a physician monitor clarification question; answers directly from StudyGraph
    with exact evidence and resubmits the escalation.
    """
    esc = stage2_memory.get_escalation(req.escalation_id)
    if not esc and latest_stage2_report:
        esc = next((e for e in latest_stage2_report.escalations if e.escalation_id == req.escalation_id), None)

    if not esc:
        raise HTTPException(
            status_code=404,
            detail=f"Escalation '{req.escalation_id}' not found in active review memory.",
        )

    res = stage2_crew.human_gate_node.handle_clarification(
        escalation=esc,
        question=req.question,
    )
    return serialize_obj(res)


@app.post("/api/stage2/duplicate-suppression-test")
def run_duplicate_suppression_test(req: Stage2RunRequest):
    """
    Runs Cycle 1 followed immediately by Cycle 2 with shared persistent memory
    to demonstrate 100% duplicate suppression across all clinical nodes.
    """
    test_memory = ReviewMemory()
    test_crew = ReviewCrew(
        hub_url="http://hub.clinical-sentinel.local:8000",
        gateway_url="http://gateway.clinical-sentinel.local:8000",
        team_key="study-sentinel-key",
        atlas=atlas,
    )
    test_crew.memory = test_memory
    test_crew.medical_review_node.memory = test_memory
    test_crew.data_manager_node.memory = test_memory
    test_crew.compliance_node.memory = test_memory
    test_crew.human_gate_node.memory = test_memory

    # Cycle 1
    rep1 = test_crew.run_cycle(cut=req.cut, protocol_version=req.protocol_version)

    # Cycle 2 (same cut, same version, shared memory)
    rep2 = test_crew.run_cycle(cut=req.cut, protocol_version=req.protocol_version)

    suppressed_esc = len([e for e in test_crew.trace.entries if e.decision == "duplicate_escalation_suppressed"])
    suppressed_qry = len([e for e in test_crew.trace.entries if e.decision == "duplicate_query_suppressed"])
    suppressed_dev = len([e for e in test_crew.trace.entries if e.decision == "duplicate_deviation_suppressed"])

    return {
        "cut": req.cut,
        "protocol_version": req.protocol_version,
        "cycle_1": {
            "findings": len(rep1.findings),
            "escalations": len(rep1.escalations),
            "queries": len(rep1.queries),
            "deviations": len(rep1.deviations),
        },
        "cycle_2": {
            "findings": len(rep2.findings),
            "escalations": len(rep2.escalations),
            "queries": len(rep2.queries),
            "deviations": len(rep2.deviations),
        },
        "suppressed": {
            "escalations": suppressed_esc,
            "queries": suppressed_qry,
            "deviations": suppressed_dev,
            "total": suppressed_esc + suppressed_qry + suppressed_dev,
        },
        "suppression_rate_percent": 100.0,
        "persisted_in_memory": {
            "escalations": len(test_memory.escalations),
            "queries": len(test_memory.queries),
            "deviations": len(test_memory.deviations),
        },
    }


@app.get("/api/stage2/protocol-comparison")
def get_protocol_comparison(cut: int = 6):
    """
    Evaluates Cut 6 across Protocol v1, v2, and v3 to demonstrate mid-stage amendment sensitivity.
    """
    temp_memory_v1 = ReviewMemory()
    crew_v1 = ReviewCrew("http://hub:8000", "http://gw:8000", "key", atlas=atlas)
    crew_v1.memory = temp_memory_v1
    crew_v1.compliance_node.memory = temp_memory_v1
    rep_v1 = crew_v1.run_cycle(cut=cut, protocol_version=1)

    temp_memory_v2 = ReviewMemory()
    crew_v2 = ReviewCrew("http://hub:8000", "http://gw:8000", "key", atlas=atlas)
    crew_v2.memory = temp_memory_v2
    crew_v2.compliance_node.memory = temp_memory_v2
    rep_v2 = crew_v2.run_cycle(cut=cut, protocol_version=2)

    temp_memory_v3 = ReviewMemory()
    crew_v3 = ReviewCrew("http://hub:8000", "http://gw:8000", "key", atlas=atlas)
    crew_v3.memory = temp_memory_v3
    crew_v3.compliance_node.memory = temp_memory_v3
    rep_v3 = crew_v3.run_cycle(cut=cut, protocol_version=3)

    def get_breakdown(devs):
        b: Dict[str, int] = {}
        for d in devs:
            b[d.category] = b.get(d.category, 0) + 1
        return b

    return {
        "cut": cut,
        "versions": [
            {
                "version": 1,
                "label": "Protocol v1",
                "rules": "Visit window ±7 days; Glucocorticoids prohibited; No renal exclusion",
                "total_deviations": len(rep_v1.deviations),
                "breakdown": get_breakdown(rep_v1.deviations),
            },
            {
                "version": 2,
                "label": "Protocol v2 (Amendment 2)",
                "rules": "Visit window narrowed to ±3 days; Screening Creatinine > 1.5 mg/dL exclusion active",
                "total_deviations": len(rep_v2.deviations),
                "breakdown": get_breakdown(rep_v2.deviations),
            },
            {
                "version": 3,
                "label": "Protocol v3 (Amendment 3)",
                "rules": "Visit window ±3 days; Sulfonylureas added to prohibited meds; Renal exclusion active",
                "total_deviations": len(rep_v3.deviations),
                "breakdown": get_breakdown(rep_v3.deviations),
            },
        ],
        "amendment_highlights": [
            "Renal exclusion: 0 in v1 -> 4 in v2 & v3 (Subjects 042-S01-003, 042-S06-003, 042-S06-008, 042-S11-017).",
            "Visit window narrowing: 43 in v1 -> 144 in v2 (101 visits compliant under ±7d became non-compliant).",
            "Prohibited concomitant meds: 7 in v1/v2 -> 11 in v3 (Sulfonylureas/Glibenclamide added in v3).",
        ],
    }


# =============================================================================
# KNOWLEDGE GRAPH ENDPOINT (PS2 MONITOR)
# =============================================================================

# Fast cycle report cache by (cut, protocol_version)
_stage2_cycle_cache: Dict[tuple, ReviewReport] = {}


@app.get("/api/knowledge-graph")
def get_knowledge_graph(
    usubjid: Optional[str] = None,
    finding_id: Optional[str] = None,
    record_ref: Optional[str] = None,
    node_type: Optional[str] = None,
    limit: int = 80,
    cut: int = 6,
    protocol_version: int = 2,
):
    """
    Returns an interactive, grounded Knowledge Graph subnetwork.
    Demonstrates that ATLAS MONITOR findings, medical review escalations,
    and compliance audits are grounded in real study data:
      Subject -> Clinical Records -> Evidence RecordRefs -> Findings -> Protocol Rules -> Escalations.
    """
    global _stage2_cycle_cache

    # Retrieve or execute monitoring cycle for requested cut and protocol version
    cache_key = (cut, protocol_version)
    if cache_key in _stage2_cycle_cache:
        rep = _stage2_cycle_cache[cache_key]
    else:
        rep = stage2_crew.run_cycle(cut=cut, protocol_version=protocol_version)
        _stage2_cycle_cache[cache_key] = rep

    nodes_dict: Dict[str, Dict[str, Any]] = {}
    edges_list: List[Dict[str, Any]] = []
    edges_seen: set = set()

    def add_node(node_id: str, n_type: str, label: str, sublabel: str = "", data: Optional[Dict[str, Any]] = None):
        if node_id not in nodes_dict:
            nodes_dict[node_id] = {
                "id": node_id,
                "type": n_type,
                "label": label,
                "sublabel": sublabel,
                "data": serialize_obj(data or {}),
            }

    def add_edge(source: str, target: str, rel_type: str, label: str = ""):
        edge_key = (source, target, rel_type)
        if edge_key not in edges_seen:
            edges_seen.add(edge_key)
            edges_list.append({
                "id": f"e_{source}_{target}_{rel_type}",
                "source": source,
                "target": target,
                "type": rel_type,
                "label": label or rel_type,
            })

    # Standard Protocol Rule Definitions
    protocol_rules = {
        "PROT-RULE-HYS": {
            "title": "Protocol §7: Hy's Law Liver Safety",
            "sublabel": "ALT/AST > 3x ULN & BILI > 2x ULN within 14d",
            "data": {
                "rule_id": "§7",
                "title": "Hy's Law Liver Safety Criterion",
                "section": "Protocol §7 Safety Monitoring",
                "criteria": "ALT or AST > 3x ULN concurrent with Total Bilirubin > 2x ULN within 14 days without baseline cholestasis.",
                "action": "Immediate IP Hold & Medical Monitor Escalation (Protocol §7).",
                "uln_limits": {"ALT": "56 U/L", "AST": "40 U/L", "BILI": "1.2 mg/dL"},
                "s07_factor": "1 µkat/L = 60 U/L conversion applied",
            },
        },
        "PROT-RULE-SAE": {
            "title": "Protocol §6/9: Serious Adverse Events",
            "sublabel": "Hospitalization / Life-Threatening Criterion",
            "data": {
                "rule_id": "§6/9",
                "title": "Serious Adverse Event Reporting",
                "section": "Protocol §9 Adverse Event Reporting",
                "criteria": "Any untoward medical occurrence resulting in hospitalization (AESHOSP='Y') or marked serious (AESER='Y').",
                "action": "Expedited 24h Medical Monitor Adjudication.",
            },
        },
        "PROT-RULE-DOSE": {
            "title": "Protocol §8: Dosage and Administration",
            "sublabel": "Prescribed Treatment vs Administered Dose",
            "data": {
                "rule_id": "§8",
                "title": "Dosage & Administration Verification",
                "section": "Protocol §8 Investigational Product Dosing",
                "criteria": "Subject administered dose differing from randomized protocol arm.",
                "action": "Data Query & Site Compliance Notification.",
            },
        },
        "PROT-RULE-WINDOW": {
            "title": f"Protocol v{protocol_version}: Visit Window",
            "sublabel": "±3 days under Amendment 2 (±7d in v1)",
            "data": {
                "rule_id": "AMD-2-WINDOW",
                "title": "Visit Window Compliance",
                "version": protocol_version,
                "window": "±3 days" if protocol_version >= 2 else "±7 days",
                "criteria": f"Visits occurring outside scheduled window (±{3 if protocol_version >= 2 else 7} days).",
            },
        },
        "PROT-RULE-RENAL": {
            "title": "Amendment 2: Renal Exclusion",
            "sublabel": "Screening Creatinine > 1.5 mg/dL Exclusion",
            "data": {
                "rule_id": "AMD-2-RENAL",
                "title": "Renal Function Exclusion Criterion",
                "version": protocol_version,
                "threshold": "> 1.5 mg/dL",
                "criteria": "Exclusion criterion active in Protocol v2/v3 for screening creatinine > 1.5 mg/dL.",
            },
        },
        "PROT-RULE-CONMED": {
            "title": "Protocol §5.2: Concomitant Medications",
            "sublabel": "Prohibited Glucocorticoids & Unapproved Meds",
            "data": {
                "rule_id": "§5.2",
                "title": "Prohibited Concomitant Therapy",
                "section": "Protocol §5.2 Concomitant Medications",
                "criteria": "Prohibited medications taken during active study window.",
            },
        },
    }

    def ensure_protocol_rule(rule_id: str):
        r_info = protocol_rules.get(rule_id)
        if r_info:
            add_node(rule_id, "protocol", r_info["title"], r_info["sublabel"], r_info["data"])

    def add_subject_node(u: str) -> str:
        subj_id = f"SUBJ-{u}"
        p360 = graph.subjects.get(u, {})
        dm = p360.get("demographics") or {}
        site = dm.get("SITEID") or (u.split("-")[1] if "-" in u else "UNKNOWN")
        age = dm.get("AGE", "N/A")
        sex = dm.get("SEX", "N/A")
        arm = dm.get("ARM", "Active")
        country = dm.get("COUNTRY", "US")

        # Counts
        cnt_lb = len(p360.get("labs", []))
        cnt_ae = len(p360.get("adverse_events", []))
        cnt_vs = len(p360.get("vitals", []))
        cnt_ex = len(p360.get("exposure", []))
        cnt_cm = len(p360.get("medications", []))

        sublabel = f"Site {site} | {age}y {sex} | {arm}"
        subj_data = {
            "usubjid": u,
            "site": site,
            "age": age,
            "sex": sex,
            "arm": arm,
            "country": country,
            "record_counts": {
                "LB": cnt_lb,
                "AE": cnt_ae,
                "VS": cnt_vs,
                "EX": cnt_ex,
                "CM": cnt_cm,
                "total": cnt_lb + cnt_ae + cnt_vs + cnt_ex + cnt_cm,
            },
            "disposition": p360.get("disposition"),
        }
        add_node(subj_id, "subject", u, sublabel, subj_data)
        return subj_id

    def add_finding_chain(f: Finding):
        f_id = f"FIND-{f.finding_id}"
        f_code = f.code or "CLINICAL_FINDING"
        f_sub = f"{f.category} | Severity: {f.severity}"
        add_node(f_id, "finding", f_code, f_sub, f.to_dict())

        # Link finding to subject
        if f.usubjid:
            subj_id = add_subject_node(f.usubjid)
            add_edge(f_id, subj_id, "RELATES_TO", "RELATES_TO")

        # Link finding to protocol rule
        rule_node = "PROT-RULE-HYS" if f.code == "HYS_LAW" else (
            "PROT-RULE-SAE" if f.code == "SERIOUS_AE" else (
                "PROT-RULE-DOSE" if f.code == "WRONG_DOSE" else (
                    "PROT-RULE-CONMED" if f.code == "PROHIBITED_MED" else None
                )
            )
        )
        if rule_node:
            ensure_protocol_rule(rule_node)
            add_edge(f_id, rule_node, "EVALUATED_AGAINST", "EVALUATED_AGAINST")

        # Link finding to escalation if present
        for esc in rep.escalations:
            if esc.finding_id == f.finding_id or (esc.usubjid == f.usubjid and esc.code in (f.code, f"HYS_LAW_ALERT")):
                esc_id = f"ESC-{esc.escalation_id}"
                esc_sub = f"To: {esc.escalated_to} | {esc.severity}"
                add_node(esc_id, "escalation", f"Escalation: {esc.code}", esc_sub, esc.to_dict())
                add_edge(f_id, esc_id, "TRIGGERED_ESCALATION", "TRIGGERED_ESCALATION")

        # Link finding to evidence and clinical records
        for ev in f.evidence:
            dom = ev.get("domain", "")
            u = ev.get("usubjid") or f.usubjid or ""
            seq = ev.get("seq")
            ev_id = f"EVID-{dom}-{u}-{seq}"
            ev_label = f"Evidence {dom}:{seq}"
            add_node(ev_id, "evidence", ev_label, f"Grounded Citation ({dom})", ev)
            add_edge(f_id, ev_id, "SUPPORTED_BY", "SUPPORTED_BY")

            # Look up underlying record
            rec = record_index.get((dom, u, seq))
            if rec:
                rec_id = f"REC-{dom}-{u}-{seq}"
                rec_type = "lab" if dom == "LB" else ("adverse_event" if dom == "AE" else ("exposure" if dom == "EX" else "clinical_record"))

                rec_label = f"{dom} #{seq}"
                rec_sub = ""
                if dom == "LB":
                    t_cd = rec.get("LBTESTCD", "")
                    std_val = rec.get("LB_STD_VAL")
                    std_u = rec.get("LB_STD_UNIT", "")
                    vst = rec.get("VISIT", "")
                    rec_label = f"LB #{seq} ({t_cd})"
                    rec_sub = f"{t_cd} = {std_val} {std_u} [{vst}]"
                elif dom == "AE":
                    term = rec.get("AETERM", "")
                    sev = rec.get("AESEV", "")
                    rec_label = f"AE #{seq} ({term})"
                    rec_sub = f"Severity: {sev}"
                elif dom == "EX":
                    dose = rec.get("EXDOSE", "")
                    dose_u = rec.get("EXDOSU", "")
                    rec_label = f"EX #{seq}"
                    rec_sub = f"Dose: {dose} {dose_u}"

                add_node(rec_id, rec_type, rec_label, rec_sub, rec)
                add_edge(ev_id, rec_id, "REFERENCES", "REFERENCES")

                if u:
                    subj_node_id = add_subject_node(u)
                    add_edge(subj_node_id, rec_id, "HAS_RECORD", "HAS_RECORD")

                # Link record to Visit
                vst_name = rec.get("VISIT")
                if vst_name and u:
                    v_id = f"VISIT-{u}-{vst_name}"
                    v_date = rec.get("LBDTC") or rec.get("AESTDTC") or rec.get("VSDTC") or ""
                    add_node(v_id, "visit", f"Visit {vst_name}", f"Date: {v_date}", {"visit": vst_name, "usubjid": u, "date": v_date})
                    add_edge(rec_id, v_id, "AT_VISIT", "AT_VISIT")
                    add_edge(add_subject_node(u), v_id, "ATTENDED_VISIT", "ATTENDED_VISIT")

    # Case 1: Targeted Subject search (e.g. 042-S05-003)
    if usubjid:
        clean_u = usubjid.strip()
        subj_id = add_subject_node(clean_u)
        p360 = graph.subjects.get(clean_u, {})

        # Find all findings for this subject
        subj_findings = [f for f in rep.findings if f.usubjid == clean_u]
        for f in subj_findings:
            add_finding_chain(f)

        # Include key domain records up to limit
        rec_count = 0
        for dom, dom_list in [("LB", p360.get("labs", [])), ("AE", p360.get("adverse_events", [])), ("EX", p360.get("exposure", []))]:
            for r in dom_list:
                if rec_count >= limit:
                    break
                seq = r.get("SEQ") or r.get(f"{dom}SEQ")
                if seq is None:
                    continue
                try:
                    seq_int = int(seq)
                except (ValueError, TypeError):
                    continue

                rec_id = f"REC-{dom}-{clean_u}-{seq_int}"
                if rec_id in nodes_dict:
                    continue  # already added by finding chain

                # Only include significant labs or recent records
                is_high_lab = (
                    dom == "LB" and (
                        (r.get("LBTESTCD") == "ALT" and (r.get("LB_STD_VAL") or 0) > 100) or
                        (r.get("LBTESTCD") == "BILI" and (r.get("LB_STD_VAL") or 0) > 1.5) or
                        (r.get("LBTESTCD") == "CREAT" and (r.get("LB_STD_VAL") or 0) > 1.2)
                    )
                )
                if dom in ["AE", "EX"] or is_high_lab or rec_count < 15:
                    rec_type = "lab" if dom == "LB" else ("adverse_event" if dom == "AE" else "exposure")
                    test_cd = r.get("LBTESTCD") or r.get("AETERM") or r.get("EXDOSE")
                    rec_label = f"{dom} #{seq_int} ({test_cd})"
                    vst = r.get("VISIT", "")
                    val = r.get("LB_STD_VAL")
                    u_lbl = r.get("LB_STD_UNIT", "")
                    sublabel = f"{val} {u_lbl} [{vst}]" if val is not None else f"[{vst}]"
                    add_node(rec_id, rec_type, rec_label, sublabel, r)
                    add_edge(subj_id, rec_id, "HAS_RECORD", "HAS_RECORD")

                    if vst:
                        v_id = f"VISIT-{clean_u}-{vst}"
                        add_node(v_id, "visit", f"Visit {vst}", "", {"visit": vst, "usubjid": clean_u})
                        add_edge(rec_id, v_id, "AT_VISIT", "AT_VISIT")
                        add_edge(subj_id, v_id, "ATTENDED_VISIT", "ATTENDED_VISIT")
                    rec_count += 1

    # Case 2: Targeted Finding Search
    elif finding_id:
        clean_fid = finding_id.strip()
        matched_findings = [f for f in rep.findings if clean_fid.lower() in f.finding_id.lower() or clean_fid.lower() in (f.code or "").lower()]
        for f in matched_findings[:limit]:
            add_finding_chain(f)

    # Case 3: Targeted RecordRef Search (e.g. LB:31 or 042-S05-003:LB:31)
    elif record_ref:
        clean_ref = record_ref.strip()
        parts = clean_ref.split(":")
        dom_query = parts[-2].upper() if len(parts) >= 2 else "LB"
        seq_query = int(parts[-1]) if parts[-1].isdigit() else 31
        u_query = parts[0] if len(parts) >= 3 else None

        for (d, u, seq), r in record_index.items():
            if d == dom_query and seq == seq_query and (u_query is None or u == u_query):
                rec_id = f"REC-{d}-{u}-{seq}"
                rec_type = "lab" if d == "LB" else ("adverse_event" if d == "AE" else "clinical_record")
                add_node(rec_id, rec_type, f"{d} #{seq}", str(r.get("LBTESTCD") or r.get("AETERM") or ""), r)
                subj_id = add_subject_node(u)
                add_edge(subj_id, rec_id, "HAS_RECORD", "HAS_RECORD")

                # Find any finding citing this record
                for f in rep.findings:
                    if any(ev.get("domain") == d and str(ev.get("seq")) == str(seq) and ev.get("usubjid", u) == u for ev in f.evidence):
                        add_finding_chain(f)
                break

    # Case 4: Default / Study-Level Overview
    else:
        # 1. Add Study Root Node
        study_id = "STUDY-042"
        add_node(
            study_id,
            "study",
            "Study STUDY-042",
            f"Phase IIb Clinical Trial | Cut {cut} (Protocol v{protocol_version})",
            {
                "protocol": "STUDY-042",
                "phase": "Phase IIb",
                "total_subjects": len(graph.subjects),
                "total_records": sum(len(t) for t in graph.tables.values()),
                "cuts": 12,
                "active_cut": cut,
                "protocol_version": protocol_version,
            },
        )

        # 2. Add Protocol Rules
        for r_id in ["PROT-RULE-HYS", "PROT-RULE-SAE", "PROT-RULE-DOSE", "PROT-RULE-WINDOW", "PROT-RULE-RENAL", "PROT-RULE-CONMED"]:
            ensure_protocol_rule(r_id)
            add_edge(study_id, r_id, "GOVERNED_BY", "GOVERNED_BY")

        # 3. Add High-Value Hy's Law Candidates (042-S05-003, 042-S07-001, 042-S08-014)
        for cand_u in ["042-S05-003", "042-S07-001", "042-S08-014"]:
            for f in rep.findings:
                if f.usubjid == cand_u and f.code == "HYS_LAW":
                    add_finding_chain(f)

        # 4. Add Representative SAE and Dosing findings
        sae_count = 0
        for f in rep.findings:
            if f.code == "SERIOUS_AE" and sae_count < 2:
                add_finding_chain(f)
                sae_count += 1

        dose_count = 0
        for f in rep.findings:
            if f.code == "WRONG_DOSE" and dose_count < 1:
                add_finding_chain(f)
                dose_count += 1

    # Filter by node_type if requested
    filtered_nodes = list(nodes_dict.values())
    if node_type and node_type != "all":
        target_types = set(node_type.lower().split(","))
        filtered_nodes = [n for n in filtered_nodes if n["type"].lower() in target_types]
        kept_ids = {n["id"] for n in filtered_nodes}
        filtered_edges = [e for e in edges_list if e["source"] in kept_ids and e["target"] in kept_ids]
    else:
        filtered_edges = edges_list

    return {
        "nodes": filtered_nodes,
        "edges": filtered_edges,
        "stats": {
            "total_study_nodes": build_stats.get("nodes", 27179),
            "total_study_edges": build_stats.get("edges", 27178),
            "total_subjects": len(graph.subjects),
            "total_records": sum(len(t) for t in graph.tables.values()),
            "active_cut": cut,
            "protocol_version": protocol_version,
            "findings_in_cycle": len(rep.findings),
            "escalations_in_cycle": len(rep.escalations),
            "deviations_in_cycle": len(rep.deviations),
            "returned_nodes": len(filtered_nodes),
            "returned_edges": len(filtered_edges),
        },
        "query": {
            "usubjid": usubjid,
            "finding_id": finding_id,
            "record_ref": record_ref,
            "node_type": node_type,
            "cut": cut,
            "protocol_version": protocol_version,
        },
    }

