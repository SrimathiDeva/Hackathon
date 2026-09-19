"""
tests/test_phase5_stress.py

Phase 5: ATLAS Robustness + Judge Stress Test Suite.
Validates:
  1. Natural Language Query Variations (COUNT, LOOKUP, HYS LAW, DOSING, PROTOCOL, WITHDRAWAL)
  2. Adversarial & Unsupported Queries (cancer, died, blood pressure 2020)
  3. Empty Results Trap (S01 wrong dose -> [] and 0 evidence)
  4. Subject ID Extraction (042-S01-001, 042-S07-001, 042-S08-014)
  5. Site Extraction (S01, S05, S07, S08 without subject confusion)
  6. Temporal Language Parsing (within 7 days, within 3 days, before Week 8, after Week 8, on the same date)
  7. Unit Language Consistency (ALT above 3 times ULN, ALT greater than three times ULN, ALT > 3x ULN)
  8. Protocol Version Context (v1 -> +-7d, v2 -> +-3d/200 corrections, v3 -> Sulfonylurea)
  9. Evidence Grounding & Zero Fabrication Verification
  10. Execution Time Profiling (Min, Max, Avg)
"""

import os
import sys
import time
import json
from typing import List, Dict, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from stage1.study_graph import StudyGraph
from stage1.atlas import Atlas
from stage1.nlu import AtlasNLU
from stage1.query_engine import AtlasQuery, QueryParser, QueryPlanner, QueryExecutor
from audit import load_raw_tables, verify_ref


def run_stress_test():
    print("=" * 80)
    print("PHASE 5: ATLAS ROBUSTNESS & JUDGE STRESS TEST")
    print("=" * 80)

    data_dir = os.path.join(BASE_DIR, "data", "hackathon-data")
    graph = StudyGraph(data_dir)
    stats = graph.build()
    print(f"StudyGraph loaded: {stats['subjects']} subjects, {stats['total_records']} records.\n")

    atlas = Atlas(graph)
    nlu = AtlasNLU(atlas=atlas, graph=graph)
    qe = QueryExecutor(graph=graph, atlas=atlas, nlu=nlu)
    parser = QueryParser()
    raw_tables = load_raw_tables()

    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    unsupported_count = 0
    empty_count = 0
    execution_times: List[float] = []

    def assert_test(name: str, condition: bool, detail: str = ""):
        nonlocal total_tests, passed_tests, failed_tests
        total_tests += 1
        if condition:
            passed_tests += 1
            print(f"  [PASS] {name} {f'({detail})' if detail else ''}")
        else:
            failed_tests += 1
            print(f"  [FAIL] {name} {f'({detail})' if detail else ''}")

    # =========================================================================
    # 1. STRESS TEST NATURAL LANGUAGE QUERIES (Intent Variations)
    # =========================================================================
    print("-" * 80)
    print("1. NATURAL LANGUAGE QUERY VARIATIONS")
    print("-" * 80)

    # 1.1 COUNT VARIATIONS
    count_variations = [
        "How many subjects are in the study?",
        "How many patients are enrolled?",
        "What is the total number of subjects?",
    ]
    for q in count_variations:
        t0 = time.perf_counter()
        res = qe.execute(q)
        dt = time.perf_counter() - t0
        execution_times.append(dt)
        assert_test(
            f"COUNT variation: '{q}'",
            res["answer"] == 241 and res["parsed_query"]["intent"] == "COUNT" and len(res["evidence"]) == 241,
            f"answer={res['answer']}, time={dt*1000:.1f}ms"
        )

    # 1.2 PATIENT LOOKUP VARIATIONS
    lookup_variations = [
        "What is the sex of 042-S07-001?",
        "Is 042-S07-001 male or female?",
        "Tell me the sex for subject 042-S07-001",
    ]
    for q in lookup_variations:
        t0 = time.perf_counter()
        res = qe.execute(q)
        dt = time.perf_counter() - t0
        execution_times.append(dt)
        assert_test(
            f"LOOKUP variation: '{q}'",
            res["answer"] == "M" and res["parsed_query"]["intent"] == "LOOKUP" and res["parsed_query"].get("subjects") == ["042-S07-001"],
            f"answer='{res['answer']}', time={dt*1000:.1f}ms"
        )

    # 1.3 HY'S LAW VARIATIONS
    hys_variations = [
        "Which subjects triggered Hy's Law?",
        "Find Hy's Law candidates",
        "Show me patients meeting Hy's Law criteria",
    ]
    expected_hys = ["042-S05-003", "042-S07-001", "042-S08-014"]
    for q in hys_variations:
        t0 = time.perf_counter()
        res = qe.execute(q)
        dt = time.perf_counter() - t0
        execution_times.append(dt)
        assert_test(
            f"HYS LAW variation: '{q}'",
            res["answer"] == expected_hys and len(res["evidence"]) == 6,
            f"candidates={res['answer']}, time={dt*1000:.1f}ms"
        )

    # 1.4 DOSING DEVIATION VARIATIONS
    dosing_variations = [
        "Which subjects received the wrong dose?",
        "Find dosing errors",
        "Which patients had dosing deviations?",
    ]
    for q in dosing_variations:
        t0 = time.perf_counter()
        res = qe.execute(q)
        dt = time.perf_counter() - t0
        execution_times.append(dt)
        assert_test(
            f"DOSING variation: '{q}'",
            isinstance(res["answer"], list) and len(res["answer"]) > 0 and res["parsed_query"]["intent"] == "FINDING",
            f"count={len(res['answer'])}, time={dt*1000:.1f}ms"
        )

    # 1.5 PROTOCOL COMPARISON VARIATIONS
    protocol_diff_variations = [
        "What changed between v1 and v2?",
        "Compare protocol version 1 and version 2",
        "What are the differences between protocol v1 and v2?",
    ]
    for q in protocol_diff_variations:
        t0 = time.perf_counter()
        res = qe.execute(q)
        dt = time.perf_counter() - t0
        execution_times.append(dt)
        ans = res["answer"]
        assert_test(
            f"PROTOCOL variation: '{q}'",
            isinstance(ans, dict) and ans.get("v1_window") == "±7 days" and ans.get("v2_window") == "±3 days",
            f"v1={ans.get('v1_window')}, v2={ans.get('v2_window')}, time={dt*1000:.1f}ms"
        )

    # 1.6 WITHDRAWAL VARIATIONS
    withdrawal_variations = [
        "Who withdrew?",
        "Which subjects discontinued?",
        "Show withdrawn subjects",
    ]
    for q in withdrawal_variations:
        t0 = time.perf_counter()
        res = qe.execute(q)
        dt = time.perf_counter() - t0
        execution_times.append(dt)
        assert_test(
            f"WITHDRAWAL variation: '{q}'",
            isinstance(res["answer"], list) and len(res["answer"]) == 34 and len(res["evidence"]) == 34,
            f"count={len(res['answer'])}, time={dt*1000:.1f}ms"
        )

    # =========================================================================
    # 2. ADVERSARIAL / UNSUPPORTED QUESTIONS
    # =========================================================================
    print("\n" + "-" * 80)
    print("2. ADVERSARIAL & UNSUPPORTED QUESTIONS")
    print("-" * 80)
    adversarial_queries = [
        "Which patients developed cancer?",
        "What was the average blood pressure in 2020?",
        "Which subjects died?",
    ]
    for q in adversarial_queries:
        t0 = time.perf_counter()
        res = qe.execute(q)
        dt = time.perf_counter() - t0
        execution_times.append(dt)
        is_unsupported = (
            res["answer"] is None
            and res["parsed_query"]["intent"] == "UNSUPPORTED"
            and len(res["evidence"]) == 0
            and "don't have enough data" in res["text"].lower()
        )
        if is_unsupported:
            unsupported_count += 1
        assert_test(
            f"Adversarial / Out-of-scope query: '{q}'",
            is_unsupported,
            f"answer={res['answer']}, evidence_count={len(res['evidence'])}, time={dt*1000:.1f}ms"
        )

    # =========================================================================
    # 3. EMPTY RESULTS TRAP
    # =========================================================================
    print("\n" + "-" * 80)
    print("3. EMPTY RESULTS & TRAP QUERIES")
    print("-" * 80)
    empty_query = "Which subjects at S01 received a wrong dose?"
    t0 = time.perf_counter()
    res_empty = qe.execute(empty_query)
    dt = time.perf_counter() - t0
    execution_times.append(dt)
    is_empty_valid = (
        res_empty["answer"] == []
        and len(res_empty["evidence"]) == 0
        and res_empty["validation"]["total_evidence"] == 0
        and res_empty["validation"]["unsupported_fabrication_count"] == 0
        and res_empty["parsed_query"]["intent"] == "TRAP"
    )
    if is_empty_valid:
        empty_count += 1
    assert_test(
        f"Empty Trap Query: '{empty_query}'",
        is_empty_valid,
        f"answer={res_empty['answer']}, evidence={len(res_empty['evidence'])}, time={dt*1000:.1f}ms"
    )

    # =========================================================================
    # 4. SUBJECT ID EXTRACTION
    # =========================================================================
    print("\n" + "-" * 80)
    print("4. SUBJECT ID EXTRACTION")
    print("-" * 80)
    test_subject_ids = [
        ("042-S01-001", "Tell me about 042-S01-001"),
        ("042-S07-001", "What is the status of 042-S07-001?"),
        ("042-S08-014", "Lookup subject 042-S08-014"),
    ]
    for expected_id, q_text in test_subject_ids:
        ast = parser.parse(q_text)
        assert_test(
            f"Extract USUBJID {expected_id} from '{q_text}'",
            ast.subjects == [expected_id],
            f"extracted={ast.subjects}"
        )

    # =========================================================================
    # 5. SITE EXTRACTION (Without subject confusion)
    # =========================================================================
    print("\n" + "-" * 80)
    print("5. SITE EXTRACTION (Not confused with USUBJID)")
    print("-" * 80)
    site_tests = [
        ("S01", "Which patients are at S01?"),
        ("S05", "How many subjects enrolled in S05?"),
        ("S07", "Show findings from site S07"),
        ("S08", "List visits at S08"),
    ]
    for expected_site, q_text in site_tests:
        ast = parser.parse(q_text)
        assert_test(
            f"Extract site {expected_site} from '{q_text}'",
            ast.site == expected_site and ast.subjects is None,
            f"site={ast.site}, subjects={ast.subjects}"
        )

    # Verify no site confusion when USUBJID contains S07
    ast_subj_only = parser.parse("What is the sex of 042-S07-001?")
    assert_test(
        "Subject '042-S07-001' does not create spurious site filter",
        ast_subj_only.site is None and ast_subj_only.subjects == ["042-S07-001"],
        f"site={ast_subj_only.site}, subjects={ast_subj_only.subjects}"
    )

    # =========================================================================
    # 6. TEMPORAL LANGUAGE
    # =========================================================================
    print("\n" + "-" * 80)
    print("6. TEMPORAL LANGUAGE PARSING")
    print("-" * 80)
    temporal_tests = [
        ("within 7 days", lambda t: t and t.get("operator") == "WITHIN" and t.get("days") == 7),
        ("within 3 days", lambda t: t and t.get("operator") == "WITHIN" and t.get("days") == 3),
        ("before Week 8", lambda t: t and t.get("operator") == "BEFORE" and t.get("anchor") == "WEEK8"),
        ("after Week 8", lambda t: t and t.get("operator") == "AFTER" and t.get("anchor") == "WEEK8"),
        ("on the same date", lambda t: t and t.get("operator") == "CONCURRENT" and t.get("relation") == "SAME_DATE"),
    ]
    for phrase, validator in temporal_tests:
        ast = parser.parse(f"Find records {phrase}")
        assert_test(
            f"Temporal expression: '{phrase}'",
            validator(ast.temporal),
            f"ast.temporal={ast.temporal}"
        )

    # =========================================================================
    # 7. UNIT LANGUAGE
    # =========================================================================
    print("\n" + "-" * 80)
    print("7. UNIT LANGUAGE CONSISTENCY")
    print("-" * 80)
    unit_tests = [
        "ALT above 3 times ULN",
        "ALT greater than three times ULN",
        "ALT > 3x ULN",
    ]
    parsed_conditions = []
    for q in unit_tests:
        ast = parser.parse(q)
        parsed_conditions.append(ast.condition)
        assert_test(
            f"Unit expression: '{q}'",
            ast.condition and ast.condition.get("operator") == ">" and ast.condition.get("raw_threshold") == 168.0 and ast.condition.get("central_uln") == 56.0,
            f"threshold={ast.condition.get('raw_threshold')} U/L, operator={ast.condition.get('operator')}"
        )

    # Check strict consistency among all three
    all_consistent = all(c == parsed_conditions[0] for c in parsed_conditions)
    assert_test(
        "Strict consistency across all three unit threshold expressions",
        all_consistent,
        f"equal={all_consistent}"
    )

    # =========================================================================
    # 8. PROTOCOL CONTEXT
    # =========================================================================
    print("\n" + "-" * 80)
    print("8. PROTOCOL VERSION CONTEXT")
    print("-" * 80)
    # v1 -> ±7 day visit window
    res_v1 = qe.execute("What is the visit window in protocol v1?")
    assert_test(
        "Protocol v1 context (±7 day window)",
        isinstance(res_v1["answer"], dict) and res_v1["answer"].get("window") == "±7 days" and any(e["document"] == "protocol_v1" for e in res_v1["evidence"]),
        f"window={res_v1['answer'].get('window')}"
    )

    # v2 -> ±3 day visit window + 200 corrections
    res_v2 = qe.execute("What is the visit window in protocol version 2?")
    assert_test(
        "Protocol v2 context (±3 day window + 200 corrections)",
        isinstance(res_v2["answer"], dict) and res_v2["answer"].get("window") == "±3 days" and res_v2["answer"].get("corrections") == 200,
        f"window={res_v2['answer'].get('window')}, corrections={res_v2['answer'].get('corrections')}"
    )

    # v3 -> Sulfonylurea addition
    res_v3 = qe.execute("What changes were introduced in protocol v3?")
    assert_test(
        "Protocol v3 context (Sulfonylurea background therapy)",
        isinstance(res_v3["answer"], dict) and "sulfonylurea" in str(res_v3["answer"]).lower() and any(e["document"] == "protocol_v3" for e in res_v3["evidence"]),
        f"summary={res_v3['answer'].get('summary')}"
    )

    # =========================================================================
    # 9. EVIDENCE GROUNDING & ZERO FABRICATION
    # =========================================================================
    print("\n" + "-" * 80)
    print("9. EVIDENCE GROUNDING AUDIT")
    print("-" * 80)
    grounded_queries = [
        "Which subjects at S07 had ALT above 3 times ULN within 7 days of Week 8?",
        "How many subjects are in the study?",
        "What is the sex of 042-S07-001?",
        "Which patients triggered Hy's Law?",
        "Who withdrew?",
    ]
    all_grounded_valid = True
    for q in grounded_queries:
        res = qe.execute(q)
        v = res["validation"]
        is_consistent = (
            v["verified_evidence"] <= v["total_evidence"]
            and v["unsupported_fabrication_count"] == 0
            and v["status"] == "PASS"
        )
        # Check actual RecordRefs against raw data
        for ev in res["evidence"]:
            if ev.get("domain") in raw_tables or ev.get("domain") == "DOC":
                if not verify_ref(ev, raw_tables):
                    is_consistent = False
        assert_test(
            f"Evidence grounding for: '{q[:40]}...'",
            is_consistent,
            f"total={v['total_evidence']}, verified={v['verified_evidence']}, fabrication=0"
        )
        if not is_consistent:
            all_grounded_valid = False

    # =========================================================================
    # SUMMARY REPORT
    # =========================================================================
    print("\n" + "=" * 80)
    print("PHASE 5 STRESS TEST SUMMARY")
    print("=" * 80)
    min_time = min(execution_times) * 1000 if execution_times else 0.0
    max_time = max(execution_times) * 1000 if execution_times else 0.0
    avg_time = (sum(execution_times) / len(execution_times)) * 1000 if execution_times else 0.0

    print(f"Total Tests Run:              {total_tests}")
    print(f"Passed:                       {passed_tests}")
    print(f"Failed:                       {failed_tests}")
    print(f"Unsupported queries handled:  {unsupported_count}")
    print(f"Empty trap queries handled:   {empty_count}")
    print(f"Evidence Validation:          {'100% GROUNDED & AUDITED' if all_grounded_valid else 'AUDIT FAILED'}")
    print(f"Execution Latency Min:        {min_time:.2f} ms")
    print(f"Execution Latency Max:        {max_time:.2f} ms")
    print(f"Execution Latency Avg:        {avg_time:.2f} ms")
    print("=" * 80)

    return {
        "total_tests": total_tests,
        "passed": passed_tests,
        "failed": failed_tests,
        "unsupported_count": unsupported_count,
        "empty_count": empty_count,
        "all_grounded_valid": all_grounded_valid,
        "min_time_ms": min_time,
        "max_time_ms": max_time,
        "avg_time_ms": avg_time,
    }


if __name__ == "__main__":
    results = run_stress_test()
    if results["failed"] > 0:
        sys.exit(1)
    sys.exit(0)
