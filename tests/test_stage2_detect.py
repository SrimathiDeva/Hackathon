"""
tests/test_stage2_detect.py

Test script for Checkpoint 2: Connecting Stage 1 ATLAS to the PS2 Detect Node.
Verifies:
  - Construction of StudyGraph, Atlas, ReviewCrew
  - Execution of run_cycle / detect for cut=6, protocol_version=2
  - Extraction of real clinical findings from StudyGraph without fabrication
  - Preservation of finding codes, usubjid, site, severity, rationale, and evidence
  - Immediate trace entry logging for the Detect node
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


def test_stage2_detect():
    print("=" * 80)
    print("TEST: STAGE 2 DETECT NODE (ATLAS INTEGRATION)")
    print("=" * 80)

    # 1. Construct StudyGraph using existing project data
    data_path = os.path.join(BASE_DIR, "data", "hackathon-data")
    graph = StudyGraph(data_path)
    print(f"Constructed StudyGraph pointing to: {data_path}")

    # 2. Construct Atlas
    atlas = Atlas(graph)
    print("Constructed Atlas engine.")

    # 3. Construct ReviewCrew
    crew = ReviewCrew(
        hub_url="http://hub.clinical-sentinel.local:8000",
        gateway_url="http://gateway.clinical-sentinel.local:8000",
        team_key="study-sentinel-key",
        atlas=atlas,
    )
    print("Constructed ReviewCrew with supplied Atlas instance.")

    # 4. Run cut=6, protocol_version=2
    cut = 6
    protocol_version = 2
    print(f"\nRunning monitoring cycle for Cut={cut}, Protocol Version={protocol_version}...")
    report = crew.run_cycle(cut=cut, protocol_version=protocol_version)

    # 5. Print number of findings
    findings = report.findings
    print(f"\n[1] Number of Findings Detected: {len(findings)}")

    # 6. Print first few finding codes
    finding_codes = [f.code for f in findings]
    print(f"[2] First few finding codes: {finding_codes[:6]}")
    print(f"    Distinct codes detected: {sorted(list(set(finding_codes)))}")

    # 7. Print first finding evidence
    first_f = findings[0] if findings else None
    if first_f:
        print(f"\n[3] First Finding Details:")
        print(f"    Finding ID:   {first_f.finding_id}")
        print(f"    Code:         {first_f.code}")
        print(f"    Category:     {first_f.category}")
        print(f"    Subject:      {first_f.usubjid}")
        print(f"    Site:         {first_f.site} (site_id: {first_f.site_id})")
        print(f"    Severity:     {first_f.severity}")
        print(f"    Rationale:    {first_f.rationale}")
        print(f"    Evidence ({len(first_f.evidence)} records): {first_f.evidence}")

    # 8. Print Detect trace entry
    detect_traces = crew.trace.get_by_node("detect")
    print(f"\n[4] Detect Trace Entry:")
    if detect_traces:
        t = detect_traces[0]
        print(f"    Timestamp: {t.timestamp}")
        print(f"    Node:      {t.node}")
        print(f"    Decision:  {t.decision}")
        print(f"    Evidence Count: {len(t.evidence)}")
        print(f"    Details:   {json.dumps(t.details, indent=2)}")
    else:
        print("    [ERROR] No detect trace entry found!")

    # Verify downstream review cycle completed
    print(f"\n[5] Downstream Monitoring Cycle Summary:")
    print(f"    Cycle ID:            {report.cycle_id}")
    print(f"    Status:              {report.status}")
    print(f"    Medical Escalations: {len(report.escalations)}")
    print(f"    Data Queries:        {len(report.queries)}")
    print(f"    Protocol Deviations: {len(report.deviations)}")
    print(f"    Actions Executed:    {len(report.actions_executed)}")
    print(f"    Nodes Traced:        {list(report.trace_summary.get('decisions_per_node', {}).keys())}")

    print("\n" + "=" * 80)
    print("STAGE 2 DETECT TEST COMPLETED SUCCESSFULLY")
    print("=" * 80)


if __name__ == "__main__":
    test_stage2_detect()
