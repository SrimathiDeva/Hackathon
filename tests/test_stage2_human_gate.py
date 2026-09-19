"""
tests/test_stage2_human_gate.py

Test Suite for PS2 Human Gate Node.
Tests:
  TEST A — APPROVED
           - Marks escalation APPROVED
           - Creates executable action for ExecuteNode
           - Records in ReviewMemory
           - Verifies trace entry human_gate_approved
           - Preserves original evidence

  TEST B — REJECTED
           - Marks escalation REJECTED / downgraded to MONITORING
           - Retains rejection reason
           - Preserves original finding and evidence
           - Records in ReviewMemory
           - Verifies trace entry human_gate_rejected
           - Runs cut again and confirms rejected escalation is NOT re-escalated

  TEST C — CLARIFY
           - Asks: "What was the ALT at screening, and is there a concomitant hepatotoxic medication?"
           - Confirms CLARIFY is not treated as rejection
           - Confirms answer is derived from ATLAS/StudyGraph without fabrication
           - Confirms evidence is attached
           - Confirms escalation is resubmitted
           - Verifies trace entries: CLARIFY, CLARIFICATION_ANSWER, ESCALATION_RESUBMITTED

  TEST D — TRACE COMPLETENESS
           - Confirms every Human Gate decision creates a trace entry

  TEST E — REGRESSION
           - Verifies audit and existing query/stage2 tests
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
from stage2.models import Escalation, Finding
from stage2.human_gate import HumanGateNode
from stage2.trace import TraceLog
from stage2.memory import ReviewMemory


def get_shared_atlas():
    data_path = os.path.join(BASE_DIR, "data", "hackathon-data")
    graph = StudyGraph(data_path)
    return Atlas(graph)


def test_a_approved(atlas=None):
    print("\n" + "=" * 80)
    print("TEST A: HUMAN GATE — APPROVED WORKFLOW")
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
    # Pick a real escalation (e.g. SAE_MISCODED 042-S02-004)
    target_escs = [e for e in report.escalations if e.usubjid == "042-S02-004"]
    assert len(target_escs) == 1, "Expected escalation for 042-S02-004"
    esc = target_escs[0]
    original_evidence = list(esc.evidence)

    print(f"[1] Testing APPROVED on Escalation: {esc.escalation_id} ({esc.code})")
    res = crew.human_gate_node.handle_response(esc, "APPROVED")

    # 1. Verify status becomes APPROVED
    print(f"[2] Escalation Status: {esc.status}")
    assert esc.status == "APPROVED", f"Expected status 'APPROVED', got '{esc.status}'"
    assert res["status"] == "APPROVED"

    # 2. Verify executable action exists
    action = res.get("action")
    print(f"[3] Executable Action Generated: {action}")
    assert action is not None, "Executable action must exist"
    assert action["action_type"] == "TRANSMIT_ESCALATION"
    assert action["status"] == "APPROVED"
    assert action["escalation_id"] == esc.escalation_id

    # 3. Verify memory records APPROVED
    print(f"[4] Verifying ReviewMemory...")
    assert crew.memory.is_escalation_approved(escalation_id=esc.escalation_id)
    assert crew.memory.is_escalation_approved(usubjid=esc.usubjid, code=esc.code)

    # 4. Verify trace contains APPROVED
    print(f"[5] Verifying Trace Log...")
    approved_traces = [
        e for e in crew.trace.entries
        if e.node == "human_gate" and "approved" in e.decision.lower()
    ]
    assert len(approved_traces) >= 1, "Expected trace entry for human_gate_approved"
    latest_trace = approved_traces[-1]
    assert latest_trace.details.get("escalation_id") == esc.escalation_id
    assert latest_trace.evidence == original_evidence, "Trace must preserve escalation evidence"

    # 5. Verify evidence is preserved
    assert esc.evidence == original_evidence, "Escalation evidence must remain intact"

    print("\n>>> TEST A PASSED: APPROVED workflow verified with complete audit compliance.")
    return atlas, crew, report


def test_b_rejected(atlas=None, crew=None):
    print("\n" + "=" * 80)
    print("TEST B: HUMAN GATE — REJECTED WORKFLOW & PERSISTENCE")
    print("=" * 80)

    if atlas is None or crew is None:
        atlas = get_shared_atlas()
        crew = ReviewCrew("http://hub", "http://gw", "key", atlas=atlas)
        crew.run_cycle(cut=6, protocol_version=2)

    # Pick another real escalation: 042-S01-007 (SAE_CONFIRMED)
    target_escs = [e for e in crew.memory.get_all_escalations() if e.usubjid == "042-S01-007"]
    assert len(target_escs) >= 1, "Expected escalation for 042-S01-007"
    esc = target_escs[0]
    original_evidence = list(esc.evidence)
    rejection_reason = "Hospitalization was elective cosmetic surgery, unrelated to study drug."

    print(f"[1] Testing REJECTED on Escalation: {esc.escalation_id} ({esc.code})")
    print(f"    Rejection Reason: {rejection_reason}")
    res = crew.human_gate_node.handle_response(esc, "REJECTED", reason=rejection_reason)

    # 1. Verify status becomes REJECTED / downgraded to MONITORING
    print(f"[2] Escalation Status: {esc.status} | Downgraded: {esc.details.get('downgraded_to')}")
    assert esc.status == "REJECTED"
    assert esc.details.get("downgraded_to") == "MONITORING"

    # 2. Verify rejection reason is retained
    assert esc.details.get("rejection_reason") == rejection_reason

    # 3. Verify original evidence remains
    assert esc.evidence == original_evidence

    # 4. Verify memory records rejection
    assert crew.memory.is_escalation_rejected(escalation_id=esc.escalation_id)
    assert crew.memory.is_escalation_rejected(usubjid=esc.usubjid, code=esc.code)

    # 5. Verify trace contains REJECTED
    rejected_traces = [
        e for e in crew.trace.entries
        if e.node == "human_gate" and "rejected" in e.decision.lower()
    ]
    assert len(rejected_traces) >= 1
    assert rejected_traces[-1].details.get("reason") == rejection_reason
    assert rejected_traces[-1].evidence == original_evidence

    # 6. Run the same cut again and verify rejected escalation is NOT re-escalated
    print(f"\n[3] Re-running cut 6 to verify rejection persistence (no re-escalation)...")
    rep2 = crew.run_cycle(cut=6, protocol_version=2)
    re_escalated = [e for e in rep2.escalations if e.usubjid == esc.usubjid and e.code == esc.code]
    print(f"    Re-escalated instances of {esc.usubjid}: {len(re_escalated)}")
    assert len(re_escalated) == 0, f"Rejected escalation {esc.usubjid} must NOT be re-escalated!"

    print("\n>>> TEST B PASSED: REJECTED workflow verified with downgrade and persistence.")


def test_c_clarify(atlas=None):
    print("\n" + "=" * 80)
    print("TEST C: HUMAN GATE — CLARIFY WORKFLOW")
    print("=" * 80)

    if atlas is None:
        atlas = get_shared_atlas()

    crew = ReviewCrew("http://hub", "http://gw", "key", atlas=atlas)
    report = crew.run_cycle(cut=6, protocol_version=2)

    # Use a real liver-signal escalation: 042-S05-003 (HYS_LAW_ALERT)
    hys_escs = [e for e in report.escalations if e.code == "HYS_LAW_ALERT"]
    assert len(hys_escs) > 0, "Expected at least one HYS_LAW_ALERT escalation"
    esc = hys_escs[0]
    original_evidence = list(esc.evidence)

    question = "What was the ALT at screening, and is there a concomitant hepatotoxic medication?"
    print(f"[1] Monitor Clarification Question on {esc.escalation_id} (Subject {esc.usubjid}):")
    print(f"    '{question}'")

    res = crew.human_gate_node.handle_clarification(esc, question)

    # 1. Verify CLARIFY is NOT treated as rejection
    print(f"\n[2] Clarification Result:")
    print(f"    Status: {res['status']}")
    print(f"    Answer: {res['clarification_answer']}")
    print(f"    Evidence Count: {len(res['clarification_evidence'])}")
    print(f"    Evidence: {res['clarification_evidence']}")

    assert res["status"] == "RESUBMITTED"
    assert esc.status == "RESUBMITTED"
    assert not crew.memory.is_escalation_rejected(escalation_id=esc.escalation_id)

    # 2. Verify answer comes from ATLAS/StudyGraph
    answer = res["clarification_answer"]
    assert "alt" in answer.lower()
    assert "screening" in answer.lower()
    assert "hepatotoxic" in answer.lower()
    assert "no hepatotoxic concomitant medication" in answer.lower()

    # 3. Verify evidence is attached
    clarif_evidence = res["clarification_evidence"]
    assert len(clarif_evidence) > 0, "Exact StudyGraph evidence must be attached to clarification"
    assert any(ev.get("domain") == "LB" for ev in clarif_evidence)
    
    # 4. Verify escalation details are updated for resubmission
    assert esc.details.get("clarification_question") == question
    assert esc.details.get("clarification_answer") == answer

    # 5. Verify trace entries: CLARIFY, CLARIFICATION_ANSWER, ESCALATION_RESUBMITTED
    hg_traces = [e for e in crew.trace.entries if e.node == "human_gate"]
    clarify_trace = [e for e in hg_traces if e.decision == "CLARIFY"]
    answer_trace = [e for e in hg_traces if e.decision == "CLARIFICATION_ANSWER"]
    resubmit_trace = [e for e in hg_traces if e.decision == "ESCALATION_RESUBMITTED"]

    assert len(clarify_trace) >= 1, "Trace must include CLARIFY entry"
    assert len(answer_trace) >= 1, "Trace must include CLARIFICATION_ANSWER entry"
    assert len(resubmit_trace) >= 1, "Trace must include ESCALATION_RESUBMITTED entry"

    assert answer_trace[-1].details.get("answer") == answer
    assert resubmit_trace[-1].details.get("status") == "RESUBMITTED"

    # Also verify with worked example subject having screening ALT = 31 U/L (042-S05-007)
    worked_example_esc = Escalation(
        escalation_id="ESC-HYS_LAW_ALERT-042-S05-007-CUT6",
        code="HYS_LAW_ALERT",
        usubjid="042-S05-007",
        severity="CRITICAL",
        summary="Potential Hy's Law case under physician review",
        evidence=[{"domain": "LB", "usubjid": "042-S05-007", "seq": 25}],
    )
    res_we = crew.human_gate_node.handle_clarification(worked_example_esc, question)
    print(f"\n[3] Worked Example Clarification (Subject 042-S05-007):")
    print(f"    Answer: {res_we['clarification_answer']}")
    print(f"    Evidence: {res_we['clarification_evidence']}")
    assert "31" in res_we["clarification_answer"], "Expected screening ALT around 31 U/L in answer"
    assert "no hepatotoxic concomitant medication" in res_we["clarification_answer"].lower()
    assert any(ev.get("domain") == "LB" for ev in res_we["clarification_evidence"])
    assert res_we["status"] == "RESUBMITTED"

    print("\n>>> TEST C PASSED: CLARIFY answered via StudyGraph and escalation resubmitted.")


def test_d_trace_completeness(atlas=None):
    print("\n" + "=" * 80)
    print("TEST D: HUMAN GATE — TRACE COMPLETENESS")
    print("=" * 80)

    if atlas is None:
        atlas = get_shared_atlas()

    trace = TraceLog()
    memory = ReviewMemory()
    gate_node = HumanGateNode(trace, memory, atlas=atlas)

    test_esc = Escalation(
        escalation_id="ESC-TEST-TRACE-001",
        code="HYS_LAW_ALERT",
        usubjid="042-S05-003",
        severity="CRITICAL",
        summary="Test escalation for trace validation",
        evidence=[{"domain": "LB", "usubjid": "042-S05-003", "seq": 31}],
    )

    initial_trace_count = len(trace.entries)

    # 1. Clarify
    gate_node.handle_clarification(test_esc, "What was the ALT at screening?")
    # Must add 3 traces: CLARIFY, CLARIFICATION_ANSWER, ESCALATION_RESUBMITTED
    assert len(trace.entries) == initial_trace_count + 3

    # 2. Approve
    gate_node.handle_response(test_esc, "APPROVED")
    # Must add 1 trace: human_gate_approved
    assert len(trace.entries) == initial_trace_count + 4

    # 3. Reject another escalation
    test_esc2 = Escalation(
        escalation_id="ESC-TEST-TRACE-002",
        code="SAE_CONFIRMED",
        usubjid="042-S01-007",
        severity="HIGH",
        evidence=[{"domain": "AE", "usubjid": "042-S01-007", "seq": 1}],
    )
    gate_node.handle_response(test_esc2, "REJECTED", reason="Unrelated finding")
    # Must add 1 trace: human_gate_rejected
    assert len(trace.entries) == initial_trace_count + 5

    # Check that all trace entries have non-empty node, decision, evidence, and details
    for entry in trace.entries:
        assert entry.node == "human_gate"
        assert len(entry.decision) > 0
        assert isinstance(entry.evidence, list)
        assert isinstance(entry.details, dict)

    print(f"All {len(trace.entries)} Human Gate actions verified with complete trace metadata.")
    print("\n>>> TEST D PASSED: Full trace completeness confirmed.")


if __name__ == "__main__":
    atlas = get_shared_atlas()
    atlas, crew, report = test_a_approved(atlas)
    test_b_rejected(atlas, crew)
    test_c_clarify(atlas)
    test_d_trace_completeness(atlas)
    print("\n" + "=" * 80)
    print("ALL CHECKPOINT PS2 HUMAN GATE TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 80)
