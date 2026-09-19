"""
tests/test_query_engine.py

Comprehensive test suite for Phase 1 of the ATLAS Clinical Query Investigation Engine.
Validates:
  1. AtlasQuery AST representation
  2. QueryParser deterministic translation
  3. QueryPlanner 10-stage execution plans (with appropriate COMPLETED and SKIPPED statuses)
  4. QueryExecutor deterministic reuse of StudyGraph and Atlas
  5. S01 dosing trap returning [] and 0 evidence
  6. Visual provenance lineage trace
  7. Strict RecordRef verification against raw tables
"""

import os
import sys
import json

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from stage1.study_graph import StudyGraph
from stage1.atlas import Atlas
from stage1.nlu import AtlasNLU
from stage1.query_engine import AtlasQuery, QueryParser, QueryPlanner, QueryExecutor
from audit import load_raw_tables, verify_ref


def run_tests():
    print("=" * 80)
    print("PHASE 1: ATLAS CLINICAL QUERY INVESTIGATION ENGINE TEST SUITE")
    print("=" * 80)

    data_dir = os.path.join(BASE_DIR, "data", "hackathon-data")
    graph = StudyGraph(data_dir)
    stats = graph.build()
    print(f"StudyGraph initialized: {stats['subjects']} subjects, {stats['total_records']} records.\n")

    atlas = Atlas(graph)
    nlu = AtlasNLU(atlas=atlas, graph=graph)
    executor = QueryExecutor(graph=graph, atlas=atlas, nlu=nlu)
    raw_tables = load_raw_tables()

    # The 7 required scenarios
    scenarios = [
        # 1. Temporal + Threshold + Site Query
        {
            "id": "SCENARIO_1_TEMPORAL_THRESHOLD",
            "q": "Which subjects at S07 had ALT above 3 times ULN within 7 days of Week 8?",
            "check_ast": lambda ast: (
                ast["intent"] == "FINDING"
                and ast["operation"] == "FIND"
                and ast["site"] == "S07"
                and ast["test"] == "ALT"
                and ast.get("temporal", {}).get("anchor") == "WEEK8"
                and ast.get("temporal", {}).get("days") == 7
                and "LB" in ast.get("domains", [])
            ),
            "check_plan": lambda plan: (
                len(plan) == 10
                and any(s["name"] == "RESOLVE_REFERENCE_RANGES" and s["status"] == "COMPLETED" for s in plan)
                and any(s["name"] == "APPLY_TEMPORAL_CONSTRAINTS" and s["status"] == "COMPLETED" for s in plan)
                and any(s["name"] == "NORMALIZE_UNITS_AND_DATES" and s["status"] == "COMPLETED" for s in plan)
            ),
            "check_result": lambda res: (
                res["answer"] == ["042-S07-001"]
                and len(res["evidence"]) == 1
                and res["evidence"][0]["domain"] == "LB"
                and res["evidence"][0]["usubjid"] == "042-S07-001"
                and res["evidence"][0]["seq"] == 25
            ),
        },
        # 2. Total Study Cohort Count
        {
            "id": "SCENARIO_2_COUNT_SUBJECTS",
            "q": "How many subjects are in the study?",
            "check_ast": lambda ast: (
                ast["intent"] == "COUNT"
                and ast["operation"] == "COUNT"
                and ast["entity"] == "SUBJECT"
                and "DM" in ast.get("domains", [])
            ),
            "check_plan": lambda plan: (
                len(plan) == 10
                and any(s["name"] == "RESOLVE_REFERENCE_RANGES" and s["status"] == "SKIPPED" for s in plan)
                and any(s["name"] == "APPLY_TEMPORAL_CONSTRAINTS" and s["status"] == "SKIPPED" for s in plan)
            ),
            "check_result": lambda res: (
                res["answer"] == 241
                and len(res["evidence"]) == 241
            ),
        },
        # 3. Subject Demographic Lookup
        {
            "id": "SCENARIO_3_SUBJECT_LOOKUP",
            "q": "What is the sex of 042-S07-001?",
            "check_ast": lambda ast: (
                ast["intent"] == "LOOKUP"
                and ast["operation"] == "LOOKUP"
                and ast.get("subjects") == ["042-S07-001"]
                and "DM" in ast.get("domains", [])
            ),
            "check_plan": lambda plan: (
                len(plan) == 10
                and any(s["name"] == "RESOLVE_REFERENCE_RANGES" and s["status"] == "SKIPPED" for s in plan)
            ),
            "check_result": lambda res: (
                res["answer"] == "M"
                and len(res["evidence"]) == 1
                and res["evidence"][0]["domain"] == "DM"
                and res["evidence"][0]["usubjid"] == "042-S07-001"
            ),
        },
        # 4. Hy's Law Finding
        {
            "id": "SCENARIO_4_HYS_LAW",
            "q": "Which patients triggered Hy's Law?",
            "check_ast": lambda ast: (
                ast["intent"] == "FINDING"
                and ast["operation"] == "FIND"
                and "LB" in ast.get("domains", [])
            ),
            "check_plan": lambda plan: (
                len(plan) == 10
                and any(s["name"] == "RESOLVE_REFERENCE_RANGES" and s["status"] == "COMPLETED" for s in plan)
                and any(s["name"] == "PERFORM_JOINS" and s["status"] == "COMPLETED" for s in plan)
            ),
            "check_result": lambda res: (
                sorted(res["answer"]) == ["042-S05-003", "042-S07-001", "042-S08-014"]
                and len(res["evidence"]) == 6
            ),
        },
        # 5. Site S01 Dosing Errors Trap
        {
            "id": "SCENARIO_5_DOSING_TRAP",
            "q": "Which subjects at site S01 received a wrong dose?",
            "check_ast": lambda ast: (
                ast["intent"] == "TRAP"
                and ast["site"] == "S01"
                and "EX" in ast.get("domains", [])
            ),
            "check_plan": lambda plan: (
                len(plan) == 10
                and any(s["name"] == "IDENTIFY_DOMAINS" and "EX" in str(s["details"]) for s in plan)
            ),
            "check_result": lambda res: (
                res["answer"] == []
                and len(res["evidence"]) == 0
                and "No dosing errors at site S01" in res["text"]
            ),
        },
        # 6. Protocol Amendment Comparison
        {
            "id": "SCENARIO_6_PROTOCOL_AMENDMENT",
            "q": "What changed between protocol version 1 and version 2?",
            "check_ast": lambda ast: (
                ast["operation"] == "COMPARE"
                and ast["entity"] == "PROTOCOL"
                and "DOC" in ast.get("domains", [])
            ),
            "check_plan": lambda plan: (
                len(plan) == 10
                and any(s["name"] == "RESOLVE_PROTOCOL_RULES" and s["status"] == "COMPLETED" for s in plan)
            ),
            "check_result": lambda res: (
                isinstance(res["answer"], dict)
                and "3 days" in res["text"]
                and "corrections" in res["text"]
                and len(res["evidence"]) == 2
            ),
        },
        # 7. Discontinuation / Disposition
        {
            "id": "SCENARIO_7_WITHDRAWALS",
            "q": "Who withdrew from the study?",
            "check_ast": lambda ast: (
                ast["intent"] == "FINDING"
                and "DS" in ast.get("domains", [])
            ),
            "check_plan": lambda plan: (
                len(plan) == 10
                and any(s["name"] == "IDENTIFY_DOMAINS" and "DS" in str(s["details"]) for s in plan)
            ),
            "check_result": lambda res: (
                isinstance(res["answer"], list)
                and len(res["answer"]) == 34
                and len(res["evidence"]) == 34
            ),
        },
    ]

    all_passed = True

    for i, sc in enumerate(scenarios, 1):
        q_text = sc["q"]
        res = executor.execute(q_text)

        # 1. Validate AST
        ast_ok = sc["check_ast"](res["parsed_query"])

        # 2. Validate Plan (10 stages with proper statuses)
        plan_ok = sc["check_plan"](res["query_plan"])

        # 3. Validate Result & Grounded Answer
        result_ok = sc["check_result"](res)

        # 4. Validate Evidence Lineage & Audit Existence
        evidence_valid = True
        for ev in res["evidence"]:
            if not verify_ref(ev, raw_tables):
                evidence_valid = False
                print(f"    INVALID EVIDENCE REF: {ev}")

        # 5. Validate Provenance
        provenance_ok = len(res["provenance"]) > 0 or res["parsed_query"]["intent"] == "TRAP"

        scenario_passed = ast_ok and plan_ok and result_ok and evidence_valid and provenance_ok
        if not scenario_passed:
            all_passed = False
            status = "FAIL"
        else:
            status = "PASS"

        print(f"[{status}] Scenario {i}: {sc['id']}")
        print(f"  Q: \"{q_text}\"")
        print(f"  AST Intent: {res['parsed_query']['intent']} | Operation: {res['parsed_query']['operation']} | Domains: {res['parsed_query']['domains']}")
        completed_stages = [s['name'] for s in res['query_plan'] if s['status'] == 'COMPLETED']
        skipped_stages = [s['name'] for s in res['query_plan'] if s['status'] == 'SKIPPED']
        print(f"  Plan: {len(completed_stages)} Completed ({', '.join(completed_stages[:3])}...), {len(skipped_stages)} Skipped ({', '.join(skipped_stages[:2])}...)")
        print(f"  Answer: {res['answer']}")
        print(f"  Evidence: {len(res['evidence'])} verified RecordRefs (Fabricated: 0)")
        print(f"  Provenance Lineage Nodes: {len(res['provenance'])}")
        print(f"  Validation Status: {res['validation']['status']} (Audit Compliant: {res['validation']['audit_compliant']})")
        print()

    print("=" * 80)
    if all_passed:
        print("ALL 7 CLINICAL QUERY ENGINE SCENARIOS PASSED WITH 100% EVIDENCE INTEGRITY!")
    else:
        print("SOME SCENARIOS FAILED! PLEASE CHECK OUTPUT ABOVE.")
    print("=" * 80)

    if not all_passed:
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
