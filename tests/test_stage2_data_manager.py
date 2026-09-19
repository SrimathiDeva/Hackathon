"""
tests/test_stage2_data_manager.py

Checkpoint 4 Test Suite: PS2 Data Manager Node.
Tests:
  TEST A: Run cut=6, protocol_version=2.
          Prints and verifies:
            - total findings
            - total queries generated
            - query domains, target fields, subjects, and text
            - exact evidence preservation for each query
  TEST B: Verify Dosing (EX.EXDOSE) and AE Miscoding (AE.AESER) Queries.
          Confirms 6 dosing queries and 1 AE miscoding query for 042-S02-004.
  TEST C: Verify Selective Triage of Non-Query Findings.
          Confirms compliance, acute safety, and disposition findings record
          no_query_needed decisions in the trace log with documented reasons.
  TEST D: Run the same cut twice using persistent ReviewMemory.
          Confirms duplicate queries are suppressed (0 new queries in cycle 2)
          and duplicate_query_suppressed trace entries are recorded.
"""

import os
import sys
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from stage1.study_graph import StudyGraph
from stage1.atlas import Atlas
from stage2.crew import ReviewCrew
from stage2.data_manager import DataManagerNode
from stage2.models import Finding, Query
from stage2.trace import TraceLog
from stage2.memory import ReviewMemory


def get_shared_atlas():
    data_path = os.path.join(BASE_DIR, "data", "hackathon-data")
    graph = StudyGraph(data_path)
    return Atlas(graph)


def test_a_run_cut6_protocol_v2(atlas=None):
    print("\n" + "=" * 80)
    print("TEST A: RUN CUT=6, PROTOCOL_VERSION=2 — DATA MANAGER QUERY GENERATION")
    print("=" * 80)

    if atlas is None:
        atlas = get_shared_atlas()

    crew = ReviewCrew(
        hub_url="http://hub.clinical-sentinel.local:8000",
        gateway_url="http://gateway.clinical-sentinel.local:8000",
        team_key="study-sentinel-key",
        atlas=atlas,
    )

    report = crew.run_cycle(cut=6, protocol_version=2)
    findings = report.findings
    queries = report.queries

    print(f"\n[1] Total findings detected: {len(findings)}")
    print(f"[2] Total queries generated: {len(queries)}")

    print("\n[3] Generated Queries Summary:")
    for qry in queries:
        print(f"    - {qry.query_id} | Subject: {qry.usubjid} | Domain: {qry.domain} | Field: {qry.target_field}")
        print(f"      Text: {qry.query_text}")

    print("\n[4] Evidence Preservation per Query:")
    finding_map = {f.finding_id: f for f in findings}
    for qry in queries:
        print(f"    - Query ID: {qry.query_id} ({qry.domain}.{qry.target_field})")
        print(f"      Evidence Count: {len(qry.evidence)}")
        print(f"      Evidence: {json.dumps(qry.evidence, indent=8)}")
        
        # Verify RULE 5: Exact Evidence Integrity
        corresponding_finding = finding_map.get(qry.finding_id)
        assert corresponding_finding is not None, f"Finding {qry.finding_id} missing from report"
        assert qry.evidence == corresponding_finding.evidence, (
            f"Evidence mismatch for {qry.query_id}: Query evidence does not match Finding evidence!"
        )

    # Assertions
    assert len(findings) == 33, f"Expected 33 findings, got {len(findings)}"
    assert len(queries) == 7, f"Expected 7 queries, got {len(queries)}"
    assert all(qry.evidence for qry in queries), "All queries must have non-empty evidence"
    print("\n>>> TEST A PASSED: All findings and queries verified with full evidence integrity.")
    return atlas, crew, report


def test_b_dosing_and_ae_miscoding_queries(atlas=None, report=None):
    print("\n" + "=" * 80)
    print("TEST B: VERIFY DOSING (EX.EXDOSE) AND AE MISCODING (AE.AESER) QUERIES")
    print("=" * 80)

    if atlas is None or report is None:
        atlas = get_shared_atlas()
        crew = ReviewCrew("http://hub", "http://gw", "key", atlas=atlas)
        report = crew.run_cycle(cut=6, protocol_version=2)

    queries = report.queries

    # 1. Dosing Queries on EX.EXDOSE
    dosing_queries = [q for q in queries if q.domain == "EX" and q.target_field == "EXDOSE"]
    print(f"\n[1] Dosing queries generated on EX.EXDOSE: {len(dosing_queries)}")
    assert len(dosing_queries) == 6, f"Expected 6 dosing queries, got {len(dosing_queries)}"
    
    for q in dosing_queries:
        assert q.usubjid is not None, "Dosing query must have usubjid"
        assert "dosing" in q.query_text.lower() or "exdose" in q.query_text.lower()
        assert len(q.evidence) > 0, "Dosing query must have evidence"
        assert all(ev.get("domain") == "EX" for ev in q.evidence), "Evidence must point to EX domain"
        print(f"    - Confirmed EX.EXDOSE query for subject: {q.usubjid}")

    # 2. AE Miscoding Query on AE.AESER for subject 042-S02-004
    ae_queries = [q for q in queries if q.domain == "AE" and q.target_field == "AESER"]
    print(f"\n[2] AE Miscoding queries generated on AE.AESER: {len(ae_queries)}")
    assert len(ae_queries) == 1, f"Expected exactly 1 AE miscoding query, got {len(ae_queries)}"
    s02_qry = ae_queries[0]
    
    assert s02_qry.usubjid == "042-S02-004", f"Expected query for 042-S02-004, got {s02_qry.usubjid}"
    assert "hospital" in s02_qry.query_text.lower()
    assert "aeser" in s02_qry.query_text.lower()
    assert len(s02_qry.evidence) > 0, "AE miscoding query must have evidence"
    assert all(ev.get("domain") == "AE" for ev in s02_qry.evidence), "Evidence must point to AE domain"
    print(f"    - Confirmed AE.AESER query for subject 042-S02-004:")
    print(f"      Text: {s02_qry.query_text}")

    print("\n>>> TEST B PASSED: Dosing and AE miscoding queries verified with exact targets.")


def test_c_selective_triage_non_query_findings(atlas=None, crew=None, report=None):
    print("\n" + "=" * 80)
    print("TEST C: VERIFY SELECTIVE TRIAGE OF NON-QUERY FINDINGS")
    print("=" * 80)

    if atlas is None or crew is None or report is None:
        atlas = get_shared_atlas()
        crew = ReviewCrew("http://hub", "http://gw", "key", atlas=atlas)
        report = crew.run_cycle(cut=6, protocol_version=2)

    queried_finding_ids = {q.finding_id for q in report.queries}

    # Findings that should NOT generate queries:
    # - PROHIBITED_MED (11) -> Compliance Node
    # - AE_DISCONTINUATION (10) -> Disposition documentation
    # - HYS_LAW (2) -> Acute Medical Monitor hold
    # - Correctly coded SERIOUS_AE (3) -> Medical Monitor escalation
    non_query_findings = [f for f in report.findings if f.finding_id not in queried_finding_ids]
    print(f"[1] Count of findings triaged as non-query: {len(non_query_findings)}")
    assert len(non_query_findings) == 26, f"Expected 26 non-query findings, got {len(non_query_findings)}"

    # Check Data Manager trace log for 'no_query_needed' decisions
    dm_traces = [e for e in crew.trace.entries if e.node == "data_manager"]
    no_query_traces = [e for e in dm_traces if e.decision == "no_query_needed"]
    print(f"[2] Count of 'no_query_needed' trace entries: {len(no_query_traces)}")
    assert len(no_query_traces) == 26, f"Expected 26 no_query_needed trace entries, got {len(no_query_traces)}"

    for tr in no_query_traces:
        details = tr.details or {}
        assert "reason" in details and len(details["reason"]) > 10, "Trace entry must contain clinical rationale"
        assert len(tr.evidence) > 0, "Trace entry must include evidence"

    print("\n>>> TEST C PASSED: Non-query findings correctly triaged and traced with justifications.")


def test_d_persistent_memory_duplicate_query_suppression(atlas=None):
    print("\n" + "=" * 80)
    print("TEST D: PERSISTENT REVIEWMEMORY DUPLICATE QUERY SUPPRESSION")
    print("=" * 80)

    if atlas is None:
        atlas = get_shared_atlas()

    persistent_memory = ReviewMemory()

    crew = ReviewCrew(
        hub_url="http://hub.clinical-sentinel.local:8000",
        gateway_url="http://gateway.clinical-sentinel.local:8000",
        team_key="study-sentinel-key",
        atlas=atlas,
    )
    crew.memory = persistent_memory
    crew.data_manager_node.memory = persistent_memory
    crew.medical_review_node.memory = persistent_memory

    # Cycle 1
    print("\n[1] Running Cycle 1 (Cut 6, Protocol v2)...")
    rep1 = crew.run_cycle(cut=6, protocol_version=2)
    print(f"    Cycle 1 Findings: {len(rep1.findings)}")
    print(f"    Cycle 1 Queries:  {len(rep1.queries)}")
    assert len(rep1.queries) == 7, f"Expected 7 queries in Cycle 1, got {len(rep1.queries)}"

    # Cycle 2 (Same cut with persistent memory)
    print("\n[2] Running Cycle 2 (Cut 6, Protocol v2) with Persistent ReviewMemory...")
    rep2 = crew.run_cycle(cut=6, protocol_version=2)
    print(f"    Cycle 2 Findings: {len(rep2.findings)}")
    print(f"    Cycle 2 Queries:  {len(rep2.queries)}")
    assert len(rep2.queries) == 0, (
        f"Expected 0 new queries in Cycle 2 due to duplicate suppression, got {len(rep2.queries)}"
    )

    # Check duplicate suppression trace entries
    suppressed_traces = [
        e for e in crew.trace.entries
        if e.node == "data_manager" and e.decision == "duplicate_query_suppressed"
    ]
    print(f"\n[3] Duplicate suppression trace entries recorded: {len(suppressed_traces)}")
    assert len(suppressed_traces) == 7, (
        f"Expected 7 duplicate_query_suppressed trace entries, got {len(suppressed_traces)}"
    )

    for tr in suppressed_traces:
        print(f"    - Suppressed query for: {tr.details.get('usubjid')} ({tr.details.get('domain')}.{tr.details.get('target_field')})")
        assert len(tr.evidence) > 0, "Suppressed trace entry must retain finding evidence"
        assert tr.details.get("usubjid") is not None

    print("\n>>> TEST D PASSED: Duplicate queries correctly suppressed via ReviewMemory.")


if __name__ == "__main__":
    atlas = get_shared_atlas()
    atlas, crew, report = test_a_run_cut6_protocol_v2(atlas)
    test_b_dosing_and_ae_miscoding_queries(atlas, report)
    test_c_selective_triage_non_query_findings(atlas, crew, report)
    test_d_persistent_memory_duplicate_query_suppression(atlas)
    print("\n" + "=" * 80)
    print("ALL CHECKPOINT 4 DATA MANAGER TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 80)
