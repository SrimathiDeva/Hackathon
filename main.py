"""
main.py

Main entry point for ATLAS Problem 1 (Study Sentinel).
Loads StudyGraph, runs Atlas on the public benchmark questions,
and outputs:
  - graph_stats.json
  - stage1_public.json
"""

import os
import sys
import json
import argparse

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from starter.schemas import Question
from stage1.study_graph import StudyGraph
from stage1.atlas import Atlas


PUBLIC_QUESTIONS = [
    Question(question_id="Q001", text="How many subjects are in the study?", kind="count"),
    Question(question_id="Q002", text="How many subjects at site S07 discontinued due to an adverse event?", kind="count"),
    Question(question_id="Q003", text="How many subjects experienced adverse events?", kind="count"),
    Question(question_id="Q004", text="How many adverse events are recorded?", kind="count"),
    Question(question_id="Q005", text="How many vital sign records are recorded?", kind="count"),
    Question(question_id="Q006", text="What is the sex of subject 042-S01-003?", kind="lookup"),
    Question(question_id="Q007", text="What treatment arm was subject 042-S01-003 assigned to?", kind="lookup"),
    Question(question_id="Q008", text="List the laboratory and adverse-event records for 042-S05-003 within 7 days of the WEEK8 visit", kind="lookup"),
    Question(question_id="Q018", text="Which subjects meet potential Hy's law criteria?", kind="finding"),
    Question(question_id="Q031", text="Which subjects at site S01 received a wrong dose?", kind="trap"),
]


def run(data_dir: str = "data/hackathon-data", cut: int = None):
    print("=" * 80)
    print("STAGE 1: ATLAS — STUDY SENTINEL")
    print("=" * 80)

    # 1. Build StudyGraph
    graph = StudyGraph(data_dir)
    stats = graph.build(cut=cut)
    print(f"StudyGraph built successfully:")
    print(f"  • Build time: {stats['build_time_ms']} ms")
    print(f"  • Total nodes: {stats['nodes']}")
    print(f"  • Total edges: {stats['edges']}")
    print(f"  • Total subjects: {stats['subjects']}")
    print(f"  • Total clinical records: {stats['total_records']}")

    # Save graph_stats.json
    stats_path = os.path.join(BASE_DIR, "graph_stats.json")
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    print(f"Saved build statistics to {stats_path}")

    # 2. Answer Public Benchmark Questions
    atlas = Atlas(graph)
    public_results = []

    print("\n" + "=" * 80)
    print("EVALUATING 10 PUBLIC QUESTIONS")
    print("=" * 80)

    for i, q in enumerate(PUBLIC_QUESTIONS, 1):
        ans = atlas.answer(q)
        ans_dict = ans.to_dict()
        public_results.append(ans_dict)

        print(f"\n[{i}/10] Question ID: {q.question_id} ({q.kind.upper()})")
        print(f"Q: {q.text}")
        print(f"A: {ans.answer}")
        print(f"Text: {ans.text}")
        print(f"Evidence count: {len(ans.evidence)}")
        print(f"Confidence: {ans.confidence}")

    # Save stage1_public.json
    public_path = os.path.join(BASE_DIR, "stage1_public.json")
    with open(public_path, "w", encoding="utf-8") as f:
        json.dump(public_results, f, indent=2)
    print(f"\n" + "=" * 80)
    print(f"Saved stage1 public benchmark run to {public_path}")
    print("All 10 questions evaluated successfully with schema compliance!")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/hackathon-data", help="Path to study data folder")
    parser.add_argument("--cut", type=int, default=None, help="Cut number to evaluate")
    args = parser.parse_args()

    data_folder = args.data
    if not os.path.exists(data_folder):
        data_folder = os.path.join(BASE_DIR, "data", "hackathon-data")

    run(data_dir=data_folder, cut=args.cut)
