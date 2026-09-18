"""
test_foundation.py

Validates the foundation:
  1. starter/schemas.py classes
  2. stage1/study_graph.py StudyGraph loading and indexing
  3. Patient 360 lookup for 042-S07-001
  4. Unit conversion for S07 ALT (3.995 ukat/L -> 239.7 U/L)
  5. Date parsing and comma decimal handling
"""

import os
import sys
import json

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from starter.schemas import RecordRef, Question, Answer
from stage1.study_graph import StudyGraph, parse_date, parse_number


def run_tests():
    print("==================================================")
    print("STEP 1: Testing starter/schemas.py")
    print("==================================================")
    q = Question(question_id="Q001", text="How many subjects in study?", kind="count")
    ref = RecordRef(domain="LB", usubjid="042-S07-001", seq=25)
    ans = Answer(question_id="Q001", answer=241, text="241 subjects", evidence=[ref], confidence=1.0)
    ans_dict = ans.to_dict()
    assert ans_dict["answer"] == 241
    assert ans_dict["evidence"][0]["seq"] == 25
    print("Schemas working correctly!")
    print("Sample Answer output:", json.dumps(ans_dict, indent=2))

    print("\n==================================================")
    print("STEP 2: Testing Utility Parsers")
    print("==================================================")
    # Date parsing
    assert parse_date("2026-03-30") is not None
    assert parse_date("30-Mar-2026") is not None
    assert parse_date("28-May-1953") is not None
    assert parse_date("invalid") is None
    print("Date parser passed: ISO & DD-Mon-YYYY parsed successfully.")

    # Number parsing
    assert parse_number("12.4") == 12.4
    assert parse_number("12,4") == 12.4  # comma decimal
    assert parse_number("<5") is None   # below detection -> not 0
    assert parse_number("ND") is None   # not done -> not 0
    assert parse_number("") is None
    print("Number parser passed: comma decimals, '<5', 'ND' handled safely.")

    print("\n==================================================")
    print("STEP 3: Building StudyGraph")
    print("==================================================")
    data_dir = os.path.join(BASE_DIR, "data", "hackathon-data")
    graph = StudyGraph(data_dir)
    stats = graph.build()

    print(f"Build completed in {stats['build_time_ms']} ms!")
    print(f"Total Nodes: {stats['nodes']}")
    print(f"Total Edges: {stats['edges']}")
    print(f"Total Subjects: {stats['subjects']}")
    print(f"Total Clinical Records: {stats['total_records']}")

    assert stats['subjects'] >= 240, f"Expected at least 240 subjects, got {stats['subjects']}"
    assert stats['build_time_ms'] < 1000, f"Build too slow: {stats['build_time_ms']} ms"

    print("\n==================================================")
    print("STEP 4: Testing Patient 360 for 042-S07-001")
    print("==================================================")
    p360 = graph.patient360("042-S07-001")
    assert p360, "Subject 042-S07-001 not found!"
    print("Subject found! Site:", p360["site_id"])
    print("Demographics:", p360["demographics"]["USUBJID"], p360["demographics"]["AGE"], "years,", p360["demographics"]["SEX"])
    print(f"Record counts: AE={len(p360['adverse_events'])}, LB={len(p360['labs'])}, VS={len(p360['vitals'])}, EX={len(p360['exposure'])}")

    print("\n==================================================")
    print("STEP 5: Testing Worked Example (S07 Hy's Law Labs)")
    print("==================================================")
    # Find WEEK8 labs for 042-S07-001
    week8_labs = [r for r in p360["labs"] if r.get("VISIT") == "WEEK8"]
    alt_rec = next((r for r in week8_labs if r.get("LBTESTCD") == "ALT"), None)
    bili_rec = next((r for r in week8_labs if r.get("LBTESTCD") == "BILI"), None)

    assert alt_rec is not None, "ALT record for 042-S07-001 at WEEK8 missing"
    assert bili_rec is not None, "BILI record for 042-S07-001 at WEEK8 missing"

    print("Raw ALT Record:", alt_rec["LBORRES"], alt_rec["LBORRESU"], "Seq:", alt_rec.get("SEQ"))
    print("Standard ALT Value:", alt_rec["LB_STD_VAL"], alt_rec["LB_STD_UNIT"], f"(Converted: {alt_rec['LB_CONVERTED']})")
    assert alt_rec["LB_STD_VAL"] == 239.7, f"Expected 239.7 U/L, got {alt_rec['LB_STD_VAL']}"
    assert alt_rec["LB_STD_UNIT"] == "U/L"

    print("Raw BILI Record:", bili_rec["LBORRES"], bili_rec["LBORRESU"], "Seq:", bili_rec.get("SEQ"))
    print("Standard BILI Value:", bili_rec["LB_STD_VAL"], bili_rec["LB_STD_UNIT"])
    assert bili_rec["LB_STD_VAL"] == 5.38, f"Expected 5.38 mg/dL, got {bili_rec['LB_STD_VAL']}"

    # Save stats to graph_stats.json as required by hackathon specification
    stats_file = os.path.join(BASE_DIR, "graph_stats.json")
    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    print(f"\nSaved build stats to {stats_file}")

    print("\n>>> ALL FOUNDATION TESTS PASSED SUCCESSFULLY! <<<")


if __name__ == "__main__":
    run_tests()
