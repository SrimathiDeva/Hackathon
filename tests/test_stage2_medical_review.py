"""
tests/test_stage2_medical_review.py

Checkpoint 3 Test Suite: PS2 Medical Review Node.
Tests:
  TEST A: Run cut=6, protocol_version=2.
          Prints and verifies:
            - total findings
            - total escalations
            - escalation codes
            - escalation subjects
            - evidence for each escalation
  TEST B: Verify the AESHOSP=Y / AESER=N rule (Subject: 042-S02-004).
          Confirms hospitalization is treated as serious (SAE_MISCODED, CRITICAL).
  TEST C: Verify non-critical monitoring findings do not automatically become escalations.
          Also verifies baseline liver elevation stays monitoring-only per Rule 3.
  TEST D: Run the same cut twice using persistent ReviewMemory and confirm
          that already-created escalations are suppressed as duplicates.
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
from stage2.medical_review import MedicalReviewNode
from stage2.models import Finding, Escalation
from stage2.trace import TraceLog
from stage2.memory import ReviewMemory


def get_shared_atlas():
    data_path = os.path.join(BASE_DIR, "data", "hackathon-data")
    graph = StudyGraph(data_path)
    return Atlas(graph)


def test_a_run_cut6_protocol_v2(atlas=None):
    print("\n" + "=" * 80)
    print("TEST A: RUN CUT=6, PROTOCOL_VERSION=2 — MEDICAL REVIEW VERIFICATION")
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
    escalations = report.escalations

    print(f"\n[1] Total findings detected: {len(findings)}")
    print(f"[2] Total medical escalations created: {len(escalations)}")

    print("\n[3] Escalation Codes:")
    for esc in escalations:
        print(f"    - {esc.escalation_id} | Code: {esc.code} | Severity: {esc.severity} | Subject: {esc.usubjid}")

    print("\n[4] Escalation Subjects:")
    subjects = [esc.usubjid for esc in escalations]
    print(f"    Subjects with escalations: {subjects}")

    print("\n[5] Evidence for each escalation:")
    finding_map = {f.finding_id: f for f in findings}
    for esc in escalations:
        print(f"    - Escalation: {esc.escalation_id} ({esc.code})")
        print(f"      Summary: {esc.summary}")
        print(f"      Alternatives: {esc.alternatives}")
        print(f"      Evidence Count: {len(esc.evidence)}")
        print(f"      Evidence: {json.dumps(esc.evidence, indent=8)}")
        
        # Verify RULE 5: Exact Evidence Integrity
        corresponding_finding = finding_map.get(esc.finding_id)
        assert corresponding_finding is not None, f"Finding {esc.finding_id} missing from report"
        assert esc.evidence == corresponding_finding.evidence, (
            f"Evidence mismatch for {esc.escalation_id}: Escalation evidence does not match Finding evidence!"
        )

    # Assertions
    assert len(findings) == 33, f"Expected 33 findings, got {len(findings)}"
    assert len(escalations) == 6, f"Expected 6 escalations, got {len(escalations)}"
    assert all(esc.evidence for esc in escalations), "All escalations must have non-empty evidence"
    print("\n>>> TEST A PASSED: All findings and escalations verified with full evidence integrity.")
    return atlas, crew, report


def test_b_aeshosp_yes_aeser_no_rule(atlas=None, report=None):
    print("\n" + "=" * 80)
    print("TEST B: VERIFY AESHOSP=Y / AESER=N SERIOUS AE RULE (SUBJECT 042-S02-004)")
    print("=" * 80)

    if atlas is None or report is None:
        atlas = get_shared_atlas()
        crew = ReviewCrew("http://hub", "http://gw", "key", atlas=atlas)
        report = crew.run_cycle(cut=6, protocol_version=2)

    # 1. Locate subject 042-S02-004 AE record in ATLAS StudyGraph
    p360 = atlas.graph.subjects.get("042-S02-004")
    assert p360 is not None, "Subject 042-S02-004 must exist in StudyGraph"
    ae_records = p360.get("adverse_events", [])
    assert len(ae_records) > 0, "Subject 042-S02-004 must have AE records"
    
    target_ae = None
    for ae in ae_records:
        if (ae.get("AESHOSP") or "").upper() == "Y":
            target_ae = ae
            break

    assert target_ae is not None, "Subject 042-S02-004 must have an AE record with AESHOSP='Y'"
    print(f"[Dataset Record Confirmed] 042-S02-004 AE:")
    print(f"    AETERM: {target_ae.get('AETERM')}")
    print(f"    AESER:  {target_ae.get('AESER')}")
    print(f"    AESHOSP:{target_ae.get('AESHOSP')}")
    assert (target_ae.get("AESER") or "").upper() == "N", "Expected AESER='N' for 042-S02-004"
    assert (target_ae.get("AESHOSP") or "").upper() == "Y", "Expected AESHOSP='Y' for 042-S02-004"

    # 2. Check the escalation generated by Medical Review
    s02_escs = [e for e in report.escalations if e.usubjid == "042-S02-004"]
    assert len(s02_escs) == 1, f"Expected exactly 1 escalation for 042-S02-004, found {len(s02_escs)}"
    s02_esc = s02_escs[0]

    print(f"\n[Escalation Created for 042-S02-004]:")
    print(f"    Escalation ID: {s02_esc.escalation_id}")
    print(f"    Code:          {s02_esc.code}")
    print(f"    Severity:      {s02_esc.severity}")
    print(f"    Summary:       {s02_esc.summary}")
    print(f"    Evidence:      {s02_esc.evidence}")
    print(f"    Alternatives:  {s02_esc.alternatives}")

    # Confirm requirements:
    # - code: SAE_MISCODED
    # - severity: CRITICAL
    # - summary: explains hospitalization makes event serious according to protocol section 6 and expedited reporting applies
    # - exact AE evidence preserved
    # - alternatives provided
    assert s02_esc.code == "SAE_MISCODED", f"Expected code 'SAE_MISCODED', got '{s02_esc.code}'"
    assert s02_esc.severity == "CRITICAL", f"Expected severity 'CRITICAL', got '{s02_esc.severity}'"
    assert "hospitalization" in s02_esc.summary.lower(), "Summary must mention hospitalization"
    assert "section 6" in s02_esc.summary.lower() or "protocol" in s02_esc.summary.lower(), "Summary must mention protocol section 6"
    assert "expedited" in s02_esc.summary.lower(), "Summary must mention expedited reporting"
    assert len(s02_esc.evidence) > 0, "Exact AE evidence must be preserved"
    assert len(s02_esc.alternatives) >= 2, "Alternatives must be provided"

    print("\n>>> TEST B PASSED: AESHOSP=Y / AESER=N correctly recognized as serious (SAE_MISCODED, CRITICAL).")


def test_c_non_critical_monitoring_findings(atlas=None, crew=None, report=None):
    print("\n" + "=" * 80)
    print("TEST C: VERIFY NON-CRITICAL FINDINGS DO NOT AUTOMATICALLY ESCALATE")
    print("=" * 80)

    if atlas is None or crew is None or report is None:
        atlas = get_shared_atlas()
        crew = ReviewCrew("http://hub", "http://gw", "key", atlas=atlas)
        report = crew.run_cycle(cut=6, protocol_version=2)

    escalated_finding_ids = {e.finding_id for e in report.escalations}

    # Verify each category of non-critical findings
    non_critical_codes = ["WRONG_DOSE", "PROHIBITED_MED", "AE_DISCONTINUATION"]
    non_critical_findings = [f for f in report.findings if f.code in non_critical_codes]

    print(f"[1] Count of non-critical findings detected: {len(non_critical_findings)}")
    assert len(non_critical_findings) == 27, f"Expected 27 non-critical findings, got {len(non_critical_findings)}"

    for f in non_critical_findings:
        assert f.finding_id not in escalated_finding_ids, (
            f"Non-critical finding {f.finding_id} ({f.code}) was erroneously escalated!"
        )

    print("    All 27 non-critical findings remained as monitoring-only.")

    # Check that trace records 'monitoring_only' decisions with valid reasons
    trace = crew.trace.entries
    monitoring_traces = [e for e in trace if e.node == "medical_review" and e.decision == "monitoring_only"]
    print(f"[2] Count of 'monitoring_only' decisions in Medical Review trace: {len(monitoring_traces)}")
    assert len(monitoring_traces) == 27, f"Expected 27 monitoring_only trace entries, got {len(monitoring_traces)}"

    for tr in monitoring_traces:
        details = tr.details or {}
        assert "reason" in details and len(details["reason"]) > 10, "Trace entry must record a clear reason"
        assert len(tr.evidence) > 0, "Trace entry must include evidence"

    # Also verify RULE 3: Hy's Law candidate with baseline elevation stays monitoring_only
    print("\n[3] Testing Rule 3: Liver candidate with baseline elevation:")
    trace_log = TraceLog()
    memory = ReviewMemory()
    review_node = MedicalReviewNode(trace_log, memory, atlas=atlas)

    # Construct a mock finding for a hypothetical subject with pre-existing baseline ALT
    # to confirm the decision logic
    pre_existing_finding = Finding(
        finding_id="FIND-HYS-TEST-BASELINE",
        category="SAFETY",
        code="HYS_LAW",
        usubjid="MOCK-BASELINE-SUBJ",
        severity="CRITICAL",
        evidence=[{"domain": "LB", "usubjid": "MOCK-BASELINE-SUBJ", "seq": 99}],
    )

    # Monkey-patch _check_baseline_liver_elevation for this test finding to simulate baseline high
    orig_check = review_node._check_baseline_liver_elevation
    review_node._check_baseline_liver_elevation = lambda u: (
        (True, [{"domain": "LB", "usubjid": u, "seq": 1}], "ALT=180 U/L at SCREENING (> ULN 56)")
        if u == "MOCK-BASELINE-SUBJ"
        else orig_check(u)
    )

    escs = review_node.process([pre_existing_finding], cut=6, protocol_version=2)
    assert len(escs) == 0, "Hy's Law candidate with baseline elevation must NOT produce an escalation"
    
    recent_traces = [e for e in trace_log.entries if e.node == "medical_review"]
    assert len(recent_traces) == 1
    assert recent_traces[0].decision == "monitoring_only"
    assert "baseline" in recent_traces[0].details.get("reason", "").lower()
    print("    Baseline liver elevation test passed: retained as monitoring-only with documented reason.")

    print("\n>>> TEST C PASSED: Non-critical findings remain monitoring-only; trace verified.")


def test_d_persistent_memory_duplicate_suppression(atlas=None):
    print("\n" + "=" * 80)
    print("TEST D: PERSISTENT REVIEWMEMORY DUPLICATE ESCALATION SUPPRESSION")
    print("=" * 80)

    if atlas is None:
        atlas = get_shared_atlas()

    persistent_memory = ReviewMemory()
    trace = TraceLog()

    crew = ReviewCrew(
        hub_url="http://hub.clinical-sentinel.local:8000",
        gateway_url="http://gateway.clinical-sentinel.local:8000",
        team_key="study-sentinel-key",
        atlas=atlas,
    )
    crew.memory = persistent_memory
    crew.medical_review_node.memory = persistent_memory

    # Cycle 1
    print("\n[1] Running Cycle 1 (Cut 6, Protocol v2)...")
    rep1 = crew.run_cycle(cut=6, protocol_version=2)
    print(f"    Cycle 1 Findings:    {len(rep1.findings)}")
    print(f"    Cycle 1 Escalations: {len(rep1.escalations)}")
    assert len(rep1.escalations) == 6, f"Expected 6 escalations in Cycle 1, got {len(rep1.escalations)}"

    # Cycle 2 (Same cut with persistent memory)
    print("\n[2] Running Cycle 2 (Cut 6, Protocol v2) with Persistent ReviewMemory...")
    rep2 = crew.run_cycle(cut=6, protocol_version=2)
    print(f"    Cycle 2 Findings:    {len(rep2.findings)}")
    print(f"    Cycle 2 Escalations: {len(rep2.escalations)}")
    assert len(rep2.escalations) == 0, (
        f"Expected 0 new escalations in Cycle 2 due to duplicate suppression, got {len(rep2.escalations)}"
    )

    # Check duplicate suppression trace entries
    suppressed_traces = [
        e for e in crew.trace.entries
        if e.node == "medical_review" and e.decision == "duplicate_escalation_suppressed"
    ]
    print(f"\n[3] Duplicate suppression trace entries recorded: {len(suppressed_traces)}")
    assert len(suppressed_traces) == 6, (
        f"Expected 6 duplicate_escalation_suppressed trace entries, got {len(suppressed_traces)}"
    )

    for tr in suppressed_traces:
        print(f"    - Suppressed: {tr.details.get('usubjid')} ({tr.details.get('code')}) | Reason: {tr.details.get('reason')}")
        assert len(tr.evidence) > 0, "Suppressed trace entry must retain finding evidence"
        assert tr.details.get("usubjid") is not None

    print("\n>>> TEST D PASSED: Duplicate escalations correctly suppressed via ReviewMemory.")


if __name__ == "__main__":
    atlas = get_shared_atlas()
    atlas, crew, report = test_a_run_cut6_protocol_v2(atlas)
    test_b_aeshosp_yes_aeser_no_rule(atlas, report)
    test_c_non_critical_monitoring_findings(atlas, crew, report)
    test_d_persistent_memory_duplicate_suppression(atlas)
    print("\n" + "=" * 80)
    print("ALL CHECKPOINT 3 MEDICAL REVIEW TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 80)
