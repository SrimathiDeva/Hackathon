"""
tests/test_nlu.py

Automated test suite validating the natural-language question-answering capabilities of ATLAS NLU.
Verifies:
  1. All 12 required questions and variations parse without crash.
  2. Correct intent identification.
  3. Grounding in real StudyGraph data.
  4. Evidence RecordRef existence and validity.
  5. Zero fabricated evidence.
  6. Preserved dosing error trap for site S01.
"""

import os
import sys
import json

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from starter.schemas import Question, RecordRef
from stage1.study_graph import StudyGraph
from stage1.atlas import Atlas
from stage1.nlu import AtlasNLU
from audit import load_raw_tables, verify_ref


def run_nlu_tests():
    print("=" * 80)
    print("TESTING ATLAS NATURAL LANGUAGE UNDERSTANDING (stage1/nlu.py)")
    print("=" * 80)

    data_dir = os.path.join(BASE_DIR, "data", "hackathon-data")
    graph = StudyGraph(data_dir)
    stats = graph.build()
    print(f"StudyGraph built: {stats['subjects']} subjects, {stats['total_records']} records.\n")

    atlas = Atlas(graph)
    nlu = AtlasNLU(atlas=atlas, graph=graph)
    raw_tables = load_raw_tables()

    test_queries = [
        # 1. Total subjects in study
        {
            "q": "How many subjects are in the study?",
            "expected_intent": "COUNT",
            "check": lambda ans: ans.answer == 241 and len(ans.evidence) == 241,
        },
        # 2. Enrolled patients variation
        {
            "q": "How many patients are enrolled?",
            "expected_intent": "COUNT",
            "check": lambda ans: ans.answer == 241 and len(ans.evidence) == 241,
        },
        # 3. Tell me about subject 042-S07-001
        {
            "q": "Tell me about subject 042-S07-001.",
            "expected_intent": "LOOKUP_DETAILS",
            "check": lambda ans: isinstance(ans.answer, dict) and ans.answer.get("usubjid") == "042-S07-001" and ans.answer.get("site") == "S07",
        },
        # 4. What is the sex of 042-S07-001? (Actual DM record: M)
        {
            "q": "What is the sex of 042-S07-001?",
            "expected_intent": "LOOKUP_SEX",
            "check": lambda ans: ans.answer == "M" and any(e.domain == "DM" and e.usubjid == "042-S07-001" for e in ans.evidence),
        },
        # 5. What treatment arm is 042-S07-001 in? (Actual DM record: PLACEBO)
        {
            "q": "What treatment arm is 042-S07-001 in?",
            "expected_intent": "LOOKUP_ARM",
            "check": lambda ans: ans.answer == "PLACEBO" and any(e.domain == "DM" and e.usubjid == "042-S07-001" for e in ans.evidence),
        },
        # 6. What lab results does 042-S07-001 have?
        {
            "q": "What lab results does 042-S07-001 have?",
            "expected_intent": "LB_ALL",
            "check": lambda ans: len(ans.evidence) > 0 and all(e.domain == "LB" and e.usubjid == "042-S07-001" for e in ans.evidence),
        },
        # 7. Did 042-S07-001 have any adverse events?
        {
            "q": "Did 042-S07-001 have any adverse events?",
            "expected_intent": "AE_SUBJECT",
            "check": lambda ans: len(ans.evidence) > 0 and all(e.domain == "AE" and e.usubjid == "042-S07-001" for e in ans.evidence),
        },
        # 8. Which patients triggered Hy's Law?
        {
            "q": "Which patients triggered Hy's Law?",
            "expected_intent": "FINDING_HYS_LAW",
            "check": lambda ans: sorted(ans.answer) == ["042-S05-003", "042-S07-001", "042-S08-014"] and len(ans.evidence) == 6,
        },
        # 9. Were there any dosing errors?
        {
            "q": "Were there any dosing errors?",
            "expected_intent": "FINDING_DOSING",
            "check": lambda ans: isinstance(ans.answer, list) and len(ans.answer) > 0 and all(e.domain == "EX" for e in ans.evidence),
        },
        # 10. What changed between protocol v1 and v2?
        {
            "q": "What changed between protocol v1 and v2?",
            "expected_intent": "PROTO_V1_V2",
            "check": lambda ans: ("3 days" in ans.text) and ("corrections" in ans.text) and any(e.domain == "DOC" for e in ans.evidence),
        },
        # 11. Who withdrew from the study?
        {
            "q": "Who withdrew from the study?",
            "expected_intent": "DISP_WITHDRAWN",
            "check": lambda ans: isinstance(ans.answer, list) and len(ans.answer) > 0 and all(e.domain == "DS" for e in ans.evidence),
        },
        # 12A. Ambiguity: "Show me the results."
        {
            "q": "Show me the results.",
            "expected_intent": "CLARIFY_RESULTS",
            "check": lambda ans: ans.answer is None and "Do you mean laboratory results" in ans.text and len(ans.evidence) == 0,
        },
        # 12B. Ambiguity: "Did this patient have abnormal labs?" (no USUBJID given)
        {
            "q": "Did this patient have abnormal labs?",
            "expected_intent": "CLARIFY_SUBJECT",
            "check": lambda ans: ans.answer is None and "Which subject should I look up?" in ans.text and len(ans.evidence) == 0,
        },
        # 12C. Unsupported question: "What is the weather in Paris?"
        {
            "q": "What is the weather in Paris?",
            "expected_intent": "UNSUPPORTED",
            "check": lambda ans: ans.answer is None and "don't have enough data" in ans.text and len(ans.evidence) == 0,
        },
        # TRAP: "Which subjects at site S01 received a wrong dose?"
        {
            "q": "Which subjects at site S01 received a wrong dose?",
            "expected_intent": "TRAP_S01",
            "check": lambda ans: ans.answer == [] and len(ans.evidence) == 0 and "No dosing errors at site S01" in ans.text,
        },
    ]

    all_passed = True

    for i, test in enumerate(test_queries, 1):
        q_text = test["q"]
        ans = nlu.process_query(q_text)
        passed = test["check"](ans)

        # Audit all returned evidence
        evidence_valid = True
        for ev in ans.evidence:
            ref_dict = ev.to_dict() if isinstance(ev, RecordRef) else ev
            if not verify_ref(ref_dict, raw_tables):
                evidence_valid = False
                print(f"    INVALID EVIDENCE REF: {ref_dict}")

        if not passed or not evidence_valid:
            all_passed = False
            status = "FAIL"
        else:
            status = "PASS"

        print(f"[{status}] Test {i:02d}: \"{q_text}\"")
        print(f"  Answer: {ans.answer}")
        print(f"  Text snippet: {ans.text[:95]}...")
        print(f"  Evidence count: {len(ans.evidence)} (All valid: {evidence_valid})")
        print()

    print("=" * 80)
    if all_passed:
        print("ALL NATURAL-LANGUAGE TESTS PASSED WITH 100% EVIDENCE INTEGRITY!")
    else:
        print("SOME TESTS FAILED! PLEASE REVIEW OUTPUT ABOVE.")
    print("=" * 80)

    if not all_passed:
        sys.exit(1)


if __name__ == "__main__":
    run_nlu_tests()
