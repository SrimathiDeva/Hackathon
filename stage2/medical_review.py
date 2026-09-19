"""
stage2/medical_review.py

Medical Review Node for Problem Statement 2 — MONITOR.
Reviews clinical and safety findings, evaluates patient risks,
and triggers medical escalations according to clinical protocol rules.

Rules implemented:
  RULE 1 — Serious AE & Miscoding (AESER=Y or AESHOSP=Y; AESHOSP=Y + AESER=N -> SAE_MISCODED CRITICAL)
  RULE 2 — Selective Escalation (Non-critical findings remain monitoring_only)
  RULE 3 — Hy's Law Baseline Monitoring (Screening/baseline elevation -> monitoring_only)
  RULE 4 — Duplicate Suppression (Consult ReviewMemory and suppress duplicate escalations)
  RULE 5 — Evidence Integrity (Preserve Finding evidence exactly without fabrication)
  RULE 6 — Immediate Decision Tracing (escalation_created, monitoring_only, duplicate_escalation_suppressed)
  RULE 7 — Human Gate Preparation (Output structured Escalation objects)
"""

from typing import List, Dict, Any, Optional, Tuple
from stage2.models import Finding, Escalation
from stage2.trace import TraceLog
from stage2.memory import ReviewMemory
from stage1.atlas import Atlas


class MedicalReviewNode:
    """
    Medical Review Node evaluating patient safety and protocol risks.
    Triages findings into escalated items vs monitoring-only observations.
    """

    def __init__(
        self,
        trace: TraceLog,
        memory: ReviewMemory,
        atlas: Optional[Atlas] = None,
    ):
        self.trace = trace
        self.memory = memory
        self.atlas = atlas

    def process(
        self,
        findings: List[Finding],
        cut: int,
        protocol_version: int,
    ) -> List[Escalation]:
        """
        Reviews candidate findings and produces verified medical escalations.
        """
        escalations: List[Escalation] = []

        if not findings:
            self.trace.record(
                node="medical_review",
                decision="no_findings_to_evaluate",
                evidence=[],
                details={"cut": cut, "protocol_version": protocol_version, "escalation_count": 0},
            )
            return escalations

        for f in findings:
            # -----------------------------------------------------------------
            # 1. Evaluate Serious Adverse Events (RULE 1)
            # -----------------------------------------------------------------
            if f.code == "SERIOUS_AE" or (f.category == "SAFETY" and any(e.get("domain") == "AE" for e in f.evidence)):
                code, severity, summary, alternatives = self._evaluate_ae_seriousness(f)

                # Check for duplicate escalation (RULE 4)
                if self._is_duplicate_escalation(f.usubjid, code):
                    self.trace.record(
                        node="medical_review",
                        decision="duplicate_escalation_suppressed",
                        evidence=f.evidence,
                        details={
                            "finding_id": f.finding_id,
                            "code": code,
                            "usubjid": f.usubjid,
                            "reason": f"Escalation for {f.usubjid} ({code}) already exists in ReviewMemory; duplicate suppressed.",
                            "cut": cut,
                        },
                    )
                    continue

                esc_id = f"ESC-{code}-{f.usubjid}-CUT{cut}"
                esc = Escalation(
                    escalation_id=esc_id,
                    code=code,
                    finding_id=f.finding_id,
                    usubjid=f.usubjid,
                    site_id=f.site_id,
                    severity=severity,
                    summary=summary,
                    evidence=f.evidence,  # RULE 5: Preserve exact evidence
                    alternatives=alternatives,
                    details={
                        "rule": "Protocol §6 Serious Adverse Events",
                        "cut": cut,
                        "protocol_version": protocol_version,
                        "original_code": f.code,
                    },
                )
                escalations.append(esc)
                self.memory.add_escalation(esc)
                if f.usubjid:
                    self.memory.flag_subject(f.usubjid, f"MEDICAL_ESCALATION_{code}")
                if f.site_id:
                    self.memory.flag_site(f.site_id, "SITE_SAE_ESCALATION")

                # RULE 6: Immediate decision tracing
                self.trace.record(
                    node="medical_review",
                    decision="escalation_created",
                    evidence=f.evidence,
                    details={
                        "escalation_id": esc_id,
                        "code": code,
                        "usubjid": f.usubjid,
                        "severity": severity,
                        "summary": summary,
                        "alternatives": alternatives,
                    },
                )
                continue

            # -----------------------------------------------------------------
            # 2. Evaluate Hy's Law Liver Signals (RULE 3)
            # -----------------------------------------------------------------
            if f.code == "HYS_LAW":
                is_baseline_high, baseline_evidence, baseline_reason = self._check_baseline_liver_elevation(f.usubjid)
                if is_baseline_high:
                    # RULE 3: Screening value already high at baseline -> monitoring_only
                    reason = (
                        f"Liver enzyme elevation already present at baseline/screening ({baseline_reason}); "
                        f"consistent with pre-existing condition/cholestasis per Protocol §7, retained as monitoring-only."
                    )
                    self.trace.record(
                        node="medical_review",
                        decision="monitoring_only",
                        evidence=baseline_evidence or f.evidence,
                        details={
                            "finding_id": f.finding_id,
                            "code": f.code,
                            "usubjid": f.usubjid,
                            "reason": reason,
                            "cut": cut,
                        },
                    )
                    continue

                # Confirmed acute post-baseline liver injury signal -> Escalate
                code = "HYS_LAW_ALERT"
                severity = "CRITICAL"
                summary = (
                    "Potential Hy's Law case confirmed post-baseline: acute hepatotoxicity signal "
                    "requiring immediate dosing hold and medical monitor adjudication (Protocol §7)."
                )
                alternatives = [
                    "Hold investigational product immediately",
                    "Order repeat liver function panel within 48 hours",
                    "Perform viral hepatitis and autoimmune liver disease panel",
                ]

                # Check duplicate (RULE 4)
                if self._is_duplicate_escalation(f.usubjid, code):
                    self.trace.record(
                        node="medical_review",
                        decision="duplicate_escalation_suppressed",
                        evidence=f.evidence,
                        details={
                            "finding_id": f.finding_id,
                            "code": code,
                            "usubjid": f.usubjid,
                            "reason": f"Escalation for {f.usubjid} ({code}) already exists in ReviewMemory; duplicate suppressed.",
                            "cut": cut,
                        },
                    )
                    continue

                esc_id = f"ESC-{code}-{f.usubjid}-CUT{cut}"
                esc = Escalation(
                    escalation_id=esc_id,
                    code=code,
                    finding_id=f.finding_id,
                    usubjid=f.usubjid,
                    site_id=f.site_id,
                    severity=severity,
                    summary=summary,
                    evidence=f.evidence,  # RULE 5: Preserve exact evidence
                    alternatives=alternatives,
                    details={
                        "rule": "Protocol §7 Hy's Law Criteria",
                        "cut": cut,
                        "protocol_version": protocol_version,
                    },
                )
                escalations.append(esc)
                self.memory.add_escalation(esc)
                if f.usubjid:
                    self.memory.flag_subject(f.usubjid, "CRITICAL_LIVER_INJURY_SIGNAL")
                if f.site_id:
                    self.memory.flag_site(f.site_id, "SITE_HYS_LAW_CASE")

                # RULE 6: Immediate decision tracing
                self.trace.record(
                    node="medical_review",
                    decision="escalation_created",
                    evidence=f.evidence,
                    details={
                        "escalation_id": esc_id,
                        "code": code,
                        "usubjid": f.usubjid,
                        "severity": severity,
                        "summary": summary,
                    },
                )
                continue

            # -----------------------------------------------------------------
            # 3. Non-Critical Monitoring Findings (RULE 2)
            # -----------------------------------------------------------------
            # Non-critical findings (dosing errors, concomitant meds, routine withdrawals)
            # are retained as monitoring_only observations without medical escalation.
            reason = self._get_monitoring_reason(f)
            self.trace.record(
                node="medical_review",
                decision="monitoring_only",
                evidence=f.evidence,
                details={
                    "finding_id": f.finding_id,
                    "code": f.code,
                    "category": f.category,
                    "usubjid": f.usubjid,
                    "severity": f.severity,
                    "reason": reason,
                    "cut": cut,
                },
            )

        return escalations

    # -------------------------------------------------------------------------
    # Helper Evaluators
    # -------------------------------------------------------------------------
    def _evaluate_ae_seriousness(self, f: Finding) -> Tuple[str, str, str, List[str]]:
        """
        Evaluates AE seriousness according to Protocol §6:
        - Hospitalization (AESHOSP='Y') makes the event serious regardless of AESER.
        - If AESHOSP='Y' and AESER='N' -> SAE_MISCODED (CRITICAL).
        - If AESER='Y' -> SAE_CONFIRMED (HIGH).
        """
        is_miscoded = False
        ae_records = []

        if self.atlas and hasattr(self.atlas, "graph") and self.atlas.graph.subjects:
            p360 = self.atlas.graph.subjects.get(f.usubjid)
            if p360:
                ae_records = p360.get("adverse_events", [])

        # Check raw AE records for hospitalization vs serious coding
        for r in ae_records:
            hosp = (r.get("AESHOSP") or "").upper()
            ser = (r.get("AESER") or "").upper()
            matching_seq = any(ev.get("seq") == r.get("SEQ") for ev in f.evidence) or not f.evidence
            if matching_seq and hosp == "Y" and ser != "Y":
                is_miscoded = True
                break

        # Also check finding details if pre-flagged
        if is_miscoded or f.code == "SAE_MISCODED":
            return (
                "SAE_MISCODED",
                "CRITICAL",
                "Hospitalization makes the event serious according to protocol section 6 and expedited reporting applies.",
                [
                    "Recode AESER to 'Y' and submit 24-hour expedited safety report to sponsor/IRB",
                    "Query site to confirm whether hospitalization was elective or pre-planned",
                    "Downgrade with documented Medical Monitor sign-off",
                ],
            )
        else:
            return (
                "SAE_CONFIRMED",
                "HIGH",
                "Serious Adverse Event confirmed: requires expedited safety tracking and medical monitor review.",
                [
                    "Continue safety monitoring until AE resolution or stabilization",
                    "Request detailed clinical narrative and discharge summary from site investigator",
                ],
            )

    def _check_baseline_liver_elevation(self, usubjid: Optional[str]) -> Tuple[bool, List[Dict[str, Any]], str]:
        """
        RULE 3: Checks if subject had elevated liver enzymes at SCREENING or BASELINE.
        """
        if not usubjid or not self.atlas or not hasattr(self.atlas, "graph"):
            return False, [], ""

        p360 = self.atlas.graph.subjects.get(usubjid)
        if not p360:
            return False, [], ""

        baseline_ev = []
        elevations = []

        for r in p360.get("labs", []):
            visit = (r.get("VISIT") or "").upper().replace(" ", "")
            if visit in ["SCREENING", "BASELINE", "DAY1"]:
                test = r.get("LBTESTCD")
                val = r.get("LB_STD_VAL")
                if test in ["ALT", "AST", "BILI", "ALP"] and val is not None:
                    # ULN: ALT 56, AST 40, BILI 1.2
                    uln = 56.0 if test == "ALT" else 40.0 if test == "AST" else 1.2 if test == "BILI" else 120.0
                    if val > uln:
                        baseline_ev.append({"domain": "LB", "usubjid": usubjid, "seq": r.get("SEQ")})
                        elevations.append(f"{test}={val} {r.get('LB_STD_UNIT')} at {r.get('VISIT')} (> ULN {uln})")

        if baseline_ev:
            return True, baseline_ev, "; ".join(elevations)
        return False, [], ""

    def _is_duplicate_escalation(self, usubjid: Optional[str], code: str) -> bool:
        """
        RULE 4: Checks ReviewMemory to determine if the escalation was already recorded or rejected.
        """
        if not usubjid:
            return False

        if hasattr(self.memory, "is_escalation_rejected") and self.memory.is_escalation_rejected(usubjid=usubjid, code=code):
            return True

        for existing_esc in self.memory.get_all_escalations():
            if existing_esc.usubjid == usubjid and getattr(existing_esc, "code", "") == code:
                return True
        return False

    def _get_monitoring_reason(self, f: Finding) -> str:
        """
        RULE 2: Returns the non-escalation rationale for routine monitoring observations.
        """
        if f.category == "DOSING" or f.code == "WRONG_DOSE":
            return "Dosing deviation referred to Data Manager and Site Monitor; no acute clinical safety escalation required."
        elif f.category == "PROTOCOL" or f.code == "PROHIBITED_MED":
            return "Concomitant medication protocol deviation tracked for compliance; no acute clinical safety escalation required."
        elif f.category == "DISPOSITION" or f.code == "AE_DISCONTINUATION":
            return "Routine study discontinuation tracked for disposition accountability; no medical escalation required."
        return f"Non-critical finding ({f.code}); maintained as monitoring-only."
