import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from stage1.study_graph import StudyGraph
from stage1.atlas import Atlas
from stage1.nlu import AtlasNLU
from stage1.query_engine import QueryExecutor

graph = StudyGraph(os.path.join(BASE_DIR, "data", "hackathon-data"))
graph.build()
atlas = Atlas(graph)
nlu = AtlasNLU(atlas, graph)
qe = QueryExecutor(graph, atlas, nlu)

queries = [
    # Variations
    "How many subjects are in the study?",
    "How many patients are enrolled?",
    "What is the total number of subjects?",
    "What is the sex of 042-S07-001?",
    "Is 042-S07-001 male or female?",
    "Tell me the sex for subject 042-S07-001",
    "Which subjects triggered Hy's Law?",
    "Find Hy's Law candidates",
    "Show me patients meeting Hy's Law criteria",
    "Which subjects received the wrong dose?",
    "Find dosing errors",
    "Which patients had dosing deviations?",
    "What changed between v1 and v2?",
    "Compare protocol version 1 and version 2",
    "What are the differences between protocol v1 and v2?",
    "Who withdrew?",
    "Which subjects discontinued?",
    "Show withdrawn subjects",
    # Adversarial / unsupported
    "Which patients developed cancer?",
    "What was the average blood pressure in 2020?",
    "Which subjects died?",
    # Empty result trap
    "Which subjects at S01 received a wrong dose?",
]

for q in queries:
    res = qe.execute(q)
    print(f"=== Q: {q} ===")
    print(f"Intent: {res['parsed_query']['intent']} | Op: {res['parsed_query']['operation']}")
    print(f"Answer: {res['answer']}")
    print(f"Text: {res['text']}")
    print(f"Evidence count: {len(res['evidence'])}")
    print(f"Validation: {res['validation']}")
    print()
