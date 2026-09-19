"""
stage2/crew.py

ReviewCrew Orchestrator for Problem Statement 2 — MONITOR.
Coordinates the six clinical monitoring nodes:
  1. Detect
  2. Medical Review
  3. Data Manager
  4. Compliance
  5. Human Gate
  6. Execute
"""

import time
from typing import List, Dict, Any, Optional

from starter.schemas import Question, RecordRef
from stage1.atlas import Atlas
from stage2.models import Finding, Query, Escalation, Deviation, ReviewReport
from stage2.trace import TraceLog
from stage2.memory import ReviewMemory
from stage2.medical_review import MedicalReviewNode
from stage2.data_manager import DataManagerNode
from stage2.compliance import ComplianceNode
from stage2.human_gate import HumanGateNode
from stage2.execute import ExecuteNode


class ReviewCrew:
    """
    Main agent crew orchestrating the multi-agent monitoring cycle for clinical trials.
    """

    def __init__(self, hub_url: str, gateway_url: str, team_key: str, atlas: Atlas):
        self.hub_url = hub_url
        self.gateway_url = gateway_url
        self.team_key = team_key
        self.atlas = atlas

        # Shared State & Audit Infrastructure
        self.trace = TraceLog()
        self.memory = ReviewMemory()

        # Node Components
        self.medical_review_node = MedicalReviewNode(self.trace, self.memory, atlas=self.atlas)
        self.data_manager_node = DataManagerNode(self.trace, self.memory, atlas=self.atlas)
        self.compliance_node = ComplianceNode(self.trace, self.memory, atlas=self.atlas)
        self.human_gate_node = HumanGateNode(self.trace, self.memory, atlas=self.atlas)
        self.execute_node = ExecuteNode(
            self.trace,
            self.memory,
            hub_url=self.hub_url,
            gateway_url=self.gateway_url,
            team_key=self.team_key,
        )

    # -------------------------------------------------------------------------
    # Node 1: Detect
    # -------------------------------------------------------------------------
    def detect(self, cut: int, protocol_version: int) -> List[Finding]:
        """
        Detect Node.
        Connects directly to the existing Stage 1 ATLAS and StudyGraph to extract
        real clinical findings, safety signals, dosing errors, and protocol breaches
        for the specified data cut.
        """
        # Ensure StudyGraph is indexed at the requested cut
        if getattr(self.atlas.graph, "current_cut", None) != cut:
            self.atlas.graph.build(cut=cut)

        findings: List[Finding] = []

        # 1. Safety Finding: Potential Hy's Law Candidates (Protocol §7)
        hys_ans = self.atlas._find_hys_law_candidates(
            Question(question_id=f"DET_HYS_CUT{cut}", text="Which subjects meet potential Hy's law criteria?", kind="finding")
        )
        if isinstance(hys_ans.answer, list):
            for u in hys_ans.answer:
                site_id = u.split("-")[1] if "-" in u else "UNKNOWN"
                subj_evidence = [
                    e.to_dict() if hasattr(e, "to_dict") else dict(e)
                    for e in hys_ans.evidence
                    if getattr(e, "usubjid", None) == u or (isinstance(e, dict) and e.get("usubjid") == u)
                ]
                desc = "Potential Hy's Law: ALT/AST > 3x ULN and BILI > 2x ULN within 14 days without baseline cholestasis (§7)."
                findings.append(Finding(
                    finding_id=f"FIND-HYS-{u}-CUT{cut}",
                    category="SAFETY",
                    code="HYS_LAW",
                    usubjid=u,
                    site_id=site_id,
                    description=desc,
                    rationale=desc,
                    severity="CRITICAL",
                    evidence=subj_evidence,
                    details={
                        "rule": "Protocol §7 Hy's Law",
                        "cut": cut,
                        "protocol_version": protocol_version,
                        "source": "Atlas._find_hys_law_candidates",
                    },
                ))

        # 2. Safety Finding: Serious Adverse Events (Protocol §9)
        sae_ans = self.atlas._find_serious_aes(
            Question(question_id=f"DET_SAE_CUT{cut}", text="Which subjects have serious adverse events?", kind="finding"),
            site=None,
        )
        if isinstance(sae_ans.answer, list):
            for u in sae_ans.answer:
                site_id = u.split("-")[1] if "-" in u else "UNKNOWN"
                subj_evidence = [
                    e.to_dict() if hasattr(e, "to_dict") else dict(e)
                    for e in sae_ans.evidence
                    if getattr(e, "usubjid", None) == u or (isinstance(e, dict) and e.get("usubjid") == u)
                ]
                desc = "Serious Adverse Event: AE resulting in hospitalization or life-threatening criterion (AESER='Y' or AESHOSP='Y')."
                findings.append(Finding(
                    finding_id=f"FIND-SAE-{u}-CUT{cut}",
                    category="SAFETY",
                    code="SERIOUS_AE",
                    usubjid=u,
                    site_id=site_id,
                    description=desc,
                    rationale=desc,
                    severity="HIGH",
                    evidence=subj_evidence,
                    details={
                        "rule": "Protocol §9 Adverse Event Reporting",
                        "cut": cut,
                        "protocol_version": protocol_version,
                        "source": "Atlas._find_serious_aes",
                    },
                ))

        # 3. Dosing Finding: Dosing Errors / Deviations (Protocol §8)
        dose_ans = self.atlas._find_dosing_errors(
            Question(question_id=f"DET_DOSE_CUT{cut}", text="Which subjects received the wrong dose?", kind="finding"),
            site=None,
        )
        if isinstance(dose_ans.answer, list):
            for u in dose_ans.answer:
                site_id = u.split("-")[1] if "-" in u else "UNKNOWN"
                subj_evidence = [
                    e.to_dict() if hasattr(e, "to_dict") else dict(e)
                    for e in dose_ans.evidence
                    if getattr(e, "usubjid", None) == u or (isinstance(e, dict) and e.get("usubjid") == u)
                ]
                desc = "Dosing deviation: subject received dose differing from assigned protocol treatment (§8)."
                findings.append(Finding(
                    finding_id=f"FIND-DOSE-{u}-CUT{cut}",
                    category="DOSING",
                    code="WRONG_DOSE",
                    usubjid=u,
                    site_id=site_id,
                    description=desc,
                    rationale=desc,
                    severity="HIGH",
                    evidence=subj_evidence,
                    details={
                        "rule": "Protocol §8 Dosage and Administration",
                        "cut": cut,
                        "protocol_version": protocol_version,
                        "source": "Atlas._find_dosing_errors",
                    },
                ))

        # 4. Protocol Finding: Prohibited Concomitant Medications (Protocol §5.2)
        med_ans = self.atlas._find_prohibited_medications(
            Question(question_id=f"DET_MED_CUT{cut}", text="Which subjects have prohibited concomitant medications?", kind="finding"),
            site=None,
        )
        if isinstance(med_ans.answer, list):
            for u in med_ans.answer:
                site_id = u.split("-")[1] if "-" in u else "UNKNOWN"
                subj_evidence = [
                    e.to_dict() if hasattr(e, "to_dict") else dict(e)
                    for e in med_ans.evidence
                    if getattr(e, "usubjid", None) == u or (isinstance(e, dict) and e.get("usubjid") == u)
                ]
                desc = "Prohibited concomitant medication: glucocorticoid or unapproved therapy during active trial window (§5.2)."
                findings.append(Finding(
                    finding_id=f"FIND-MED-{u}-CUT{cut}",
                    category="PROTOCOL",
                    code="PROHIBITED_MED",
                    usubjid=u,
                    site_id=site_id,
                    description=desc,
                    rationale=desc,
                    severity="HIGH",
                    evidence=subj_evidence,
                    details={
                        "rule": "Protocol §5.2 Concomitant Therapy",
                        "cut": cut,
                        "protocol_version": protocol_version,
                        "source": "Atlas._find_prohibited_medications",
                    },
                ))

        # 5. Disposition Finding: Premature Discontinuation due to AE (Protocol §10)
        for u, p360 in sorted(self.atlas.graph.subjects.items()):
            ds = p360.get("disposition")
            if ds:
                decod = ds.get("DSDECOD", "").upper()
                term = ds.get("DSTERM", "").upper()
                if "ADVERSE" in decod or "ADVERSE" in term:
                    site_id = p360.get("site_id") or (u.split("-")[1] if "-" in u else "UNKNOWN")
                    seq = ds.get("SEQ") or 1
                    ref_dict = {"domain": "DS", "usubjid": u, "seq": seq}
                    desc = f"Premature study discontinuation due to adverse event: {ds.get('DSTERM', 'Adverse Event')}."
                    findings.append(Finding(
                        finding_id=f"FIND-DISC-{u}-CUT{cut}",
                        category="DISPOSITION",
                        code="AE_DISCONTINUATION",
                        usubjid=u,
                        site_id=site_id,
                        description=desc,
                        rationale=desc,
                        severity="MEDIUM",
                        evidence=[ref_dict],
                        details={
                            "rule": "Protocol §10 Subject Disposition",
                            "cut": cut,
                            "protocol_version": protocol_version,
                            "dsterm": ds.get("DSTERM"),
                            "dsdecod": ds.get("DSDECOD"),
                        },
                    ))

        # Collect flattened evidence for trace
        all_trace_evidence = []
        for f in findings:
            all_trace_evidence.extend(f.evidence)

        decision_str = f"DETECTED_{len(findings)}_FINDINGS"
        self.trace.record(
            node="detect",
            decision=decision_str,
            evidence=all_trace_evidence,
            details={
                "cut": cut,
                "protocol_version": protocol_version,
                "findings_count": len(findings),
                "finding_codes": sorted(list(set(f.code for f in findings))),
                "categories": sorted(list(set(f.category for f in findings))),
            },
        )
        return findings

    # -------------------------------------------------------------------------
    # Cycle Orchestration
    # -------------------------------------------------------------------------
    def run_cycle(self, cut: int, protocol_version: int) -> ReviewReport:
        """
        Executes a complete monitoring cycle across all six nodes.
        Returns a validated ReviewReport.
        """
        cycle_id = f"CYCLE-CUT{cut}-V{protocol_version}-{int(time.time())}"

        # 1. Detect Node
        findings = self.detect(cut=cut, protocol_version=protocol_version)

        # 2. Medical Review Node
        escalations = self.medical_review_node.process(
            findings=findings,
            cut=cut,
            protocol_version=protocol_version,
        )

        # 3. Data Manager Node
        queries = self.data_manager_node.process(
            findings=findings,
            cut=cut,
            protocol_version=protocol_version,
        )

        # 4. Compliance Node
        deviations = self.compliance_node.process(
            findings=findings,
            cut=cut,
            protocol_version=protocol_version,
        )

        # 5. Human Gate Node
        gate_result = self.human_gate_node.process(
            escalations=escalations,
            queries=queries,
            deviations=deviations,
            cut=cut,
        )

        # 6. Execute Node
        executed_actions = self.execute_node.process(
            gate_result=gate_result,
            cut=cut,
        )

        # Build comprehensive cycle report
        report = ReviewReport(
            cycle_id=cycle_id,
            cut=cut,
            protocol_version=protocol_version,
            findings=findings,
            queries=queries,
            escalations=escalations,
            deviations=deviations,
            actions_executed=executed_actions,
            trace_summary=self.trace.summary(),
            status="COMPLETED",
        )

        return report
