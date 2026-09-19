"""
tests/test_stage2_compliance.py

Checkpoint 5 Test Suite: PS2 Compliance Node.
Tests:
  TEST A: Run cut=6, protocol_version=2.
          Verifies Compliance runs successfully and produces real deviations from study data.
  TEST B: Evidence Integrity Verification.
          Verifies every deviation contains valid RecordRef evidence that actually exists in raw tables.
  TEST C: Protocol Version Sensitivity.
          Confirms compliance results strictly vary with requested protocol_version (v1 vs v2 vs v3).
  TEST D: Mid-Stage Protocol Amendment Behavior.
          Demonstrates compliant subjects becoming violations due to amendments (renal exclusion, visit window, sulfonylurea).
  TEST E: ReviewMemory Duplicate Suppression.
          Runs the same cut + protocol version twice; verifies 0 duplicates generated on second run.
  TEST F: Trace Completeness.
          Verifies Compliance node records individual decisions and COMPLIANCE_REVIEW_COMPLETE in trace.
  TEST G: Regression Suite.
          Runs audit.py and all previous test suites.
"""

import os
import sys
import json
import csv
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from stage1.study_graph import StudyGraph
from stage1.atlas import Atlas
from stage2.crew import ReviewCrew
from stage2.models import Deviation
from stage2.memory import ReviewMemory


def get_shared_atlas():
    data_path = os.path.join(BASE_DIR, "data", "hackathon-data")
    graph = StudyGraph(data_path)
    return Atlas(graph)


# -----------------------------------------------------------------------------
# TEST A: Cut 6, Protocol Version 2 Execution
# -----------------------------------------------------------------------------
def test_a_run_cut6_protocol_v2(atlas=None):
    print("\n" + "=" * 80)
    print("TEST A: RUN CUT=6, PROTOCOL_VERSION=2 — COMPLIANCE DEVIATION DETECTION")
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
    deviations = report.deviations

    print(f"\n[1] Total deviations produced: {len(deviations)}")
    category_counts = {}
    for d in deviations:
        category_counts[d.category] = category_counts.get(d.category, 0) + 1

    print("[2] Deviation Category Breakdown:")
    for cat, cnt in sorted(category_counts.items()):
        print(f"    - {cat}: {cnt}")

    # Check required fields on Deviation
    sample_dev = deviations[0]
    print(f"\n[3] Sample Deviation ({sample_dev.deviation_id}):")
    print(f"    - Subject:          {sample_dev.usubjid}")
    print(f"    - Site:             {sample_dev.site}")
    print(f"    - Category:         {sample_dev.category}")
    print(f"    - Protocol Rule:    {sample_dev.protocol_rule}")
    print(f"    - Protocol Version: {sample_dev.protocol_version}")
    print(f"    - Cut:              {sample_dev.cut}")
    print(f"    - Severity:         {sample_dev.severity}")
    print(f"    - Explanation:      {sample_dev.explanation}")
    print(f"    - Evidence:         {json.dumps(sample_dev.evidence, indent=8)}")

    assert len(deviations) > 0, "Compliance node must produce real deviations from study data"
    assert "VISIT_WINDOW" in category_counts, "Must detect visit-window violations"
    assert "PROHIBITED_MED" in category_counts, "Must detect prohibited medications"
    assert "ELIGIBILITY" in category_counts, "Must detect eligibility violations"
    assert "RENAL_EXCLUSION" in category_counts, "Must detect renal exclusions under v2"
    assert "DOSING" in category_counts, "Must detect dosing deviations"

    # Verify all deviations have required attributes
    for d in deviations:
        assert d.usubjid, f"Deviation {d.deviation_id} missing usubjid"
        assert d.site, f"Deviation {d.deviation_id} missing site"
        assert d.category, f"Deviation {d.deviation_id} missing category"
        assert d.protocol_version == 2, f"Deviation {d.deviation_id} wrong protocol_version"
        assert d.cut == 6, f"Deviation {d.deviation_id} wrong cut"
        assert d.explanation, f"Deviation {d.deviation_id} missing explanation"
        assert len(d.evidence) > 0, f"Deviation {d.deviation_id} missing evidence"

    print("\n>>> TEST A PASSED: Compliance ran successfully and produced verified deviations.")
    return atlas, crew, report


# -----------------------------------------------------------------------------
# TEST B: Evidence Integrity Verification
# -----------------------------------------------------------------------------
def test_b_evidence_integrity(atlas=None, report=None):
    print("\n" + "=" * 80)
    print("TEST B: VERIFY EVIDENCE REFERENCES ACTUALLY EXIST IN RAW STUDY DATA")
    print("=" * 80)

    if atlas is None or report is None:
        atlas = get_shared_atlas()
        crew = ReviewCrew(
            hub_url="http://hub.clinical-sentinel.local:8000",
            gateway_url="http://gateway.clinical-sentinel.local:8000",
            team_key="study-sentinel-key",
            atlas=atlas,
        )
        report = crew.run_cycle(cut=6, protocol_version=2)

    # Load raw tables directly from disk
    data_path = os.path.join(BASE_DIR, "data", "hackathon-data", "data")
    raw_tables = {}
    for d in ["DM", "AE", "LB", "VS", "EX", "CM", "DS", "MH", "EG"]:
        filepath = os.path.join(data_path, f"{d}.csv")
        with open(filepath, "r", encoding="utf-8") as f:
            raw_tables[d] = list(csv.DictReader(f))

    def verify_record_ref(ref):
        domain = ref.get("domain")
        usubjid = ref.get("usubjid")
        seq = ref.get("seq")
        if domain not in raw_tables:
            return False
        seq_col = f"{domain}SEQ"
        for row in raw_tables[domain]:
            if row.get("USUBJID") == usubjid:
                if seq is None or row.get(seq_col) == str(seq) or row.get("SEQ") == str(seq):
                    return True
        return False

    valid_count = 0
    invalid_refs = []

    for dev in report.deviations:
        for ref in dev.evidence:
            if verify_record_ref(ref):
                valid_count += 1
            else:
                invalid_refs.append((dev.deviation_id, ref))

    total_refs = valid_count + len(invalid_refs)
    print(f"[1] Total evidence RecordRefs audited: {total_refs}")
    print(f"[2] Valid evidence references found:   {valid_count}")
    print(f"[3] Invalid evidence references:       {len(invalid_refs)}")

    if invalid_refs:
        print(f"    Failed references: {invalid_refs[:5]}")

    assert len(invalid_refs) == 0, f"Found {len(invalid_refs)} invalid evidence references!"
    assert valid_count > 0, "Must have verified at least one evidence reference"
    print("\n>>> TEST B PASSED: 100% of deviation evidence references exist in raw data.")


# -----------------------------------------------------------------------------
# TEST C: Protocol Version Sensitivity
# -----------------------------------------------------------------------------
def test_c_protocol_version_sensitivity(atlas=None):
    print("\n" + "=" * 80)
    print("TEST C: VERIFY PROTOCOL VERSION IS ACTUALLY USED (v1 vs v2 vs v3)")
    print("=" * 80)

    if atlas is None:
        atlas = get_shared_atlas()

    # Run cycle with Protocol v1
    crew_v1 = ReviewCrew("http://hub:8000", "http://gw:8000", "key", atlas=atlas)
    rep_v1 = crew_v1.run_cycle(cut=6, protocol_version=1)
    cats_v1 = {}
    for d in rep_v1.deviations:
        cats_v1[d.category] = cats_v1.get(d.category, 0) + 1

    # Run cycle with Protocol v2
    crew_v2 = ReviewCrew("http://hub:8000", "http://gw:8000", "key", atlas=atlas)
    rep_v2 = crew_v2.run_cycle(cut=6, protocol_version=2)
    cats_v2 = {}
    for d in rep_v2.deviations:
        cats_v2[d.category] = cats_v2.get(d.category, 0) + 1

    # Run cycle with Protocol v3
    crew_v3 = ReviewCrew("http://hub:8000", "http://gw:8000", "key", atlas=atlas)
    rep_v3 = crew_v3.run_cycle(cut=6, protocol_version=3)
    cats_v3 = {}
    for d in rep_v3.deviations:
        cats_v3[d.category] = cats_v3.get(d.category, 0) + 1

    print(f"[1] Protocol v1: {len(rep_v1.deviations)} total deviations -> {cats_v1}")
    print(f"[2] Protocol v2: {len(rep_v2.deviations)} total deviations -> {cats_v2}")
    print(f"[3] Protocol v3: {len(rep_v3.deviations)} total deviations -> {cats_v3}")

    # Verify Protocol Version Sensitivity:
    # 1. Renal exclusion is 0 in v1, and 4 in v2/v3
    assert cats_v1.get("RENAL_EXCLUSION", 0) == 0, "Renal exclusion must NOT be active in Protocol v1"
    assert cats_v2.get("RENAL_EXCLUSION", 0) == 4, "Renal exclusion must be active in Protocol v2 (4 deviations)"
    assert cats_v3.get("RENAL_EXCLUSION", 0) == 4, "Renal exclusion must be active in Protocol v3 (4 deviations)"

    # 2. Visit windows are ±7 days in v1 (43 deviations) vs ±3 days in v2/v3 (144 deviations)
    assert cats_v1.get("VISIT_WINDOW", 0) < cats_v2.get("VISIT_WINDOW", 0), (
        "Narrowed window in v2 must detect more visit deviations than v1"
    )
    assert cats_v1.get("VISIT_WINDOW") == 43, f"Expected 43 visit deviations in v1, got {cats_v1.get('VISIT_WINDOW')}"
    assert cats_v2.get("VISIT_WINDOW") == 144, f"Expected 144 visit deviations in v2, got {cats_v2.get('VISIT_WINDOW')}"

    # 3. Prohibited meds: only Glucocorticoids in v1/v2 (7 deviations); Sulfonylureas added in v3 (11 deviations)
    assert cats_v1.get("PROHIBITED_MED", 0) == 7, "Expected 7 prohibited meds under v1"
    assert cats_v2.get("PROHIBITED_MED", 0) == 7, "Expected 7 prohibited meds under v2"
    assert cats_v3.get("PROHIBITED_MED", 0) == 11, "Expected 11 prohibited meds under v3 (Glucocorticoids + Sulfonylureas)"

    print("\n>>> TEST C PASSED: Compliance results dynamically reflect the requested protocol version.")


# -----------------------------------------------------------------------------
# TEST D: Mid-Stage Amendment Demonstration
# -----------------------------------------------------------------------------
def test_d_mid_stage_amendment_behavior(atlas=None):
    print("\n" + "=" * 80)
    print("TEST D: VERIFY MID-STAGE PROTOCOL AMENDMENT BEHAVIOR")
    print("=" * 80)

    if atlas is None:
        atlas = get_shared_atlas()

    crew_v1 = ReviewCrew("http://hub:8000", "http://gw:8000", "key", atlas=atlas)
    rep_v1 = crew_v1.run_cycle(cut=6, protocol_version=1)

    crew_v2 = ReviewCrew("http://hub:8000", "http://gw:8000", "key", atlas=atlas)
    rep_v2 = crew_v2.run_cycle(cut=6, protocol_version=2)

    crew_v3 = ReviewCrew("http://hub:8000", "http://gw:8000", "key", atlas=atlas)
    rep_v3 = crew_v3.run_cycle(cut=6, protocol_version=3)

    # 1. Renal Exclusion Amendment Demonstration:
    # Subject 042-S01-003 has screening creatinine 1.62 mg/dL.
    # Compliant under v1; becomes a violation under v2 Amendment 2.
    u_renal = "042-S01-003"
    dev_v1_renal = [d for d in rep_v1.deviations if d.usubjid == u_renal and d.category == "RENAL_EXCLUSION"]
    dev_v2_renal = [d for d in rep_v2.deviations if d.usubjid == u_renal and d.category == "RENAL_EXCLUSION"]

    print(f"\n[1] Renal Exclusion Amendment (Subject {u_renal}):")
    print(f"    - Under Protocol v1: {len(dev_v1_renal)} deviations (Compliant - rule not active)")
    print(f"    - Under Protocol v2: {len(dev_v2_renal)} deviation  (VIOLATION: Creatinine > 1.5 mg/dL introduced in Amendment 2)")
    assert len(dev_v1_renal) == 0, "Subject must be compliant under v1"
    assert len(dev_v2_renal) == 1, "Subject must be flagged as a deviation under v2"

    # 2. Sulfonylurea Prohibited Medication Amendment Demonstration:
    # Subject 042-S05-012 received Glibenclamide (Sulfonylurea).
    # Compliant under v1 and v2; becomes a violation under v3 Amendment 3.
    u_sulfo = "042-S05-012"
    dev_v2_sulfo = [d for d in rep_v2.deviations if d.usubjid == u_sulfo and d.category == "PROHIBITED_MED"]
    dev_v3_sulfo = [d for d in rep_v3.deviations if d.usubjid == u_sulfo and d.category == "PROHIBITED_MED"]

    print(f"\n[2] Prohibited Medication Amendment (Subject {u_sulfo} on Glibenclamide):")
    print(f"    - Under Protocol v2: {len(dev_v2_sulfo)} deviations (Compliant - Sulfonylurea permitted)")
    print(f"    - Under Protocol v3: {len(dev_v3_sulfo)} deviation  (VIOLATION: Sulfonylurea prohibited under Protocol v3 §5)")
    assert len(dev_v2_sulfo) == 0, "Subject must be compliant under v2"
    assert len(dev_v3_sulfo) == 1, "Subject must be flagged as a deviation under v3"

    # 3. Visit Window Narrowing Amendment Demonstration:
    # Identify subjects compliant under ±7 days but violating ±3 days.
    v1_vis_keys = {d.details.get("key") + "@" + d.usubjid for d in rep_v1.deviations if d.category == "VISIT_WINDOW"}
    v2_new_vis = [
        d for d in rep_v2.deviations
        if d.category == "VISIT_WINDOW" and (d.details.get("key") + "@" + d.usubjid) not in v1_vis_keys
    ]
    print(f"\n[3] Visit Window Narrowing Amendment (±7 days -> ±3 days):")
    print(f"    - Total visits compliant under v1 that become violations under v2: {len(v2_new_vis)}")
    sample_vis_amend = v2_new_vis[0]
    print(f"    - Sample Subject: {sample_vis_amend.usubjid} at {sample_vis_amend.details.get('visit')}")
    print(f"      Variance: {sample_vis_amend.details.get('variance_days')} days (Within ±7d, outside ±3d)")
    assert len(v2_new_vis) > 0, "Expected multiple visits to become violations due to window narrowing"

    print("\n>>> TEST D PASSED: Mid-stage amendment behavior confirmed with real study data.")


# -----------------------------------------------------------------------------
# TEST E: ReviewMemory Duplicate Suppression
# -----------------------------------------------------------------------------
def test_e_duplicate_suppression(atlas=None):
    print("\n" + "=" * 80)
    print("TEST E: PERSISTENT REVIEWMEMORY DUPLICATE SUPPRESSION")
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
    crew.compliance_node.memory = persistent_memory
    crew.data_manager_node.memory = persistent_memory
    crew.medical_review_node.memory = persistent_memory

    # Cycle 1
    print("\n[1] Running Cycle 1 (Cut 6, Protocol v2)...")
    rep1 = crew.run_cycle(cut=6, protocol_version=2)
    print(f"    Cycle 1 Deviations: {len(rep1.deviations)}")
    assert len(rep1.deviations) == 178, f"Expected 178 deviations in Cycle 1, got {len(rep1.deviations)}"

    # Cycle 2 (Same cut & protocol version with persistent memory)
    print("\n[2] Running Cycle 2 (Cut 6, Protocol v2) with Persistent ReviewMemory...")
    rep2 = crew.run_cycle(cut=6, protocol_version=2)
    print(f"    Cycle 2 Deviations: {len(rep2.deviations)}")
    assert len(rep2.deviations) == 0, (
        f"Expected 0 new deviations in Cycle 2 due to duplicate suppression, got {len(rep2.deviations)}"
    )

    # Check duplicate suppression trace entries
    suppressed_traces = [
        e for e in crew.trace.entries
        if e.node == "compliance" and e.decision == "duplicate_deviation_suppressed"
    ]
    print(f"\n[3] Duplicate suppression trace entries recorded in trace: {len(suppressed_traces)}")
    assert len(suppressed_traces) == 178, (
        f"Expected 178 duplicate_deviation_suppressed entries, got {len(suppressed_traces)}"
    )

    # Confirm all deviations remain in persistent memory
    assert len(persistent_memory.get_all_deviations()) == 178, "All deviations must remain in memory"

    print("\n>>> TEST E PASSED: Repeated execution generates zero duplicate deviations.")


# -----------------------------------------------------------------------------
# TEST F: Trace Completeness
# -----------------------------------------------------------------------------
def test_f_trace_completeness(atlas=None, crew=None):
    print("\n" + "=" * 80)
    print("TEST F: VERIFY TRACE COMPLETENESS & COMPLIANCE DECISIONS")
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

    comp_entries = [e for e in crew.trace.entries if e.node == "compliance"]
    print(f"[1] Total Compliance trace entries: {len(comp_entries)}")

    decisions = [e.decision for e in comp_entries]
    logged_count = decisions.count("DEVIATION_LOGGED")
    print(f"[2] Individual DEVIATION_LOGGED entries: {logged_count}")
    assert logged_count == 178, f"Expected 178 DEVIATION_LOGGED entries, got {logged_count}"

    # Check summary decision
    complete_entries = [e for e in comp_entries if e.decision == "COMPLIANCE_REVIEW_COMPLETE"]
    print(f"[3] COMPLIANCE_REVIEW_COMPLETE entries: {len(complete_entries)}")
    assert len(complete_entries) == 1, "Must have exactly 1 COMPLIANCE_REVIEW_COMPLETE entry"

    summary_entry = complete_entries[0]
    print(f"[4] Summary trace details: {summary_entry.details}")
    assert summary_entry.details.get("deviation_count") == 178
    assert summary_entry.details.get("protocol_version") == 2
    assert summary_entry.details.get("cut") == 6
    assert "category_breakdown" in summary_entry.details

    print("\n>>> TEST F PASSED: Trace completeness verified with real counts and category breakdown.")


# -----------------------------------------------------------------------------
# TEST G: Full Regression Suite
# -----------------------------------------------------------------------------
def test_g_full_regression():
    print("\n" + "=" * 80)
    print("TEST G: REGRESSION SUITE (AUDIT.PY + ALL TEST SUITES)")
    print("=" * 80)

    commands = [
        ("python audit.py", "python audit.py"),
        ("tests/test_query_engine.py", f"python {os.path.join(BASE_DIR, 'tests', 'test_query_engine.py')}"),
        ("tests/test_stage2_detect.py", f"python {os.path.join(BASE_DIR, 'tests', 'test_stage2_detect.py')}"),
        ("tests/test_stage2_medical_review.py", f"python {os.path.join(BASE_DIR, 'tests', 'test_stage2_medical_review.py')}"),
        ("tests/test_stage2_data_manager.py", f"python {os.path.join(BASE_DIR, 'tests', 'test_stage2_data_manager.py')}"),
    ]

    for label, cmd in commands:
        print(f"\n--- Running: {label} ---")
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=BASE_DIR)
        print(f"Exit code: {res.returncode}")
        if res.returncode != 0:
            print("STDOUT:", res.stdout[-500:] if res.stdout else "")
            print("STDERR:", res.stderr[-500:] if res.stderr else "")
            assert False, f"Regression test {label} failed!"
        else:
            # Print brief summary
            out_lines = [l for l in res.stdout.splitlines() if "PASSED" in l or "OK" in l or "Audit" in l]
            for l in out_lines[-3:]:
                print(f"  {l}")

    print("\n>>> TEST G PASSED: Full regression suite succeeded with zero regressions.")


# -----------------------------------------------------------------------------
# Main Runner
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("STARTING CHECKPOINT 5: PS2 COMPLIANCE NODE TEST SUITE")
    print("=" * 80)

    atlas = get_shared_atlas()

    atlas, crew, report = test_a_run_cut6_protocol_v2(atlas)
    test_b_evidence_integrity(atlas, report)
    test_c_protocol_version_sensitivity(atlas)
    test_d_mid_stage_amendment_behavior(atlas)
    test_e_duplicate_suppression(atlas)
    test_f_trace_completeness(atlas, crew)
    test_g_full_regression()

    print("\n" + "=" * 80)
    print("ALL CHECKPOINT 5 COMPLIANCE NODE TESTS (A through G) PASSED PERFECTLY!")
    print("=" * 80)
