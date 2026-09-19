"""
stage2/human_gate.py

Human Gate Node for Problem Statement 2 — MONITOR.
Models the Medical Monitor's human oversight over clinical trial escalations.

Supports the three canonical responses:
  1. APPROVED:
     - Marks escalation as APPROVED
     - Creates executable action for ExecuteNode
     - Records human decision in ReviewMemory
     - Preserves original escalation evidence exactly
     - Writes immediate trace entry ('human_gate_approved')

  2. REJECTED:
     - Marks escalation as REJECTED
     - Downgrades to MONITORING state with rejection reason
     - Preserves original finding and evidence
     - Prevents duplicate escalation in subsequent cycles
     - Records rejection in ReviewMemory
     - Writes immediate trace entry ('human_gate_rejected')

  3. CLARIFY:
     - NOT a rejection; preserves escalation as pending/resubmitted
     - Answers question using real ATLAS/StudyGraph data without fabrication
     - Attaches exact evidence from StudyGraph
     - Creates clarification response and resubmits escalation
     - Writes immediate trace entries for CLARIFY, CLARIFICATION_ANSWER, and ESCALATION_RESUBMITTED
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from stage2.models import Escalation, Query, Deviation
from stage2.trace import TraceLog
from stage2.memory import ReviewMemory
from stage1.atlas import Atlas


class HumanGateNode:
    """
    Acts as the clinical safety review valve and human gate.
    Triages actions into approved, rejected (downgraded to monitoring),
    or clarified with factual study-graph evidence before resubmission.
    """

    def __init__(
        self,
        trace: TraceLog,
        memory: ReviewMemory,
        atlas: Optional[Atlas] = None,
        auto_approve_standard: bool = False,
    ):
        self.trace = trace
        self.memory = memory
        self.atlas = atlas
        self.auto_approve_standard = auto_approve_standard

    # -------------------------------------------------------------------------
    # Monitor Response Simulation / API
    # -------------------------------------------------------------------------
    def handle_response(
        self,
        escalation: Escalation,
        response: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Handles physician monitor response: APPROVED or REJECTED.
        """
        resp_upper = response.upper().strip()

        if resp_upper == "APPROVED":
            escalation.status = "APPROVED"

            # Create an executable action for ExecuteNode
            action = {
                "action_type": "TRANSMIT_ESCALATION",
                "escalation_id": escalation.escalation_id,
                "usubjid": escalation.usubjid,
                "code": escalation.code,
                "severity": escalation.severity,
                "summary": escalation.summary,
                "evidence": escalation.evidence,  # Exact evidence preserved
                "status": "APPROVED",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Record in ReviewMemory
            self.memory.record_escalation_decision(
                escalation_id=escalation.escalation_id,
                response="APPROVED",
                usubjid=escalation.usubjid,
                code=escalation.code,
            )

            # Write immediate trace entry
            self.trace.record(
                node="human_gate",
                decision="human_gate_approved",
                evidence=escalation.evidence,
                details={
                    "escalation_id": escalation.escalation_id,
                    "usubjid": escalation.usubjid,
                    "code": escalation.code,
                    "decision": "APPROVED",
                    "status": "APPROVED",
                    "action": action,
                },
            )

            return {
                "status": "APPROVED",
                "escalation": escalation,
                "action": action,
                "evidence": escalation.evidence,
            }

        elif resp_upper == "REJECTED":
            escalation.status = "REJECTED"
            escalation.details["status"] = "MONITORING"
            escalation.details["downgraded_to"] = "MONITORING"
            escalation.details["rejection_reason"] = reason or "Rejected by Medical Monitor"

            # Record in ReviewMemory (prevents re-escalation in next cycle)
            self.memory.record_escalation_decision(
                escalation_id=escalation.escalation_id,
                response="REJECTED",
                reason=reason,
                usubjid=escalation.usubjid,
                code=escalation.code,
            )

            # Write immediate trace entry
            self.trace.record(
                node="human_gate",
                decision="human_gate_rejected",
                evidence=escalation.evidence,
                details={
                    "escalation_id": escalation.escalation_id,
                    "usubjid": escalation.usubjid,
                    "code": escalation.code,
                    "decision": "REJECTED",
                    "status": "REJECTED",
                    "downgraded_to": "MONITORING",
                    "reason": reason,
                },
            )

            return {
                "status": "REJECTED",
                "escalation": escalation,
                "downgraded_to": "MONITORING",
                "reason": reason,
                "evidence": escalation.evidence,
            }

        else:
            raise ValueError(
                f"Unsupported response: {response}. Must be 'APPROVED' or 'REJECTED'. "
                "For clarification questions, use handle_clarification()."
            )

    def handle_clarification(
        self,
        escalation: Escalation,
        question: str,
    ) -> Dict[str, Any]:
        """
        Handles physician monitor clarification request (CLARIFY):
        - CLARIFY is NOT a rejection.
        - Preserves escalation as pending/resubmitted.
        - Answers question using real ATLAS/StudyGraph data.
        - Attaches exact evidence from StudyGraph.
        - Creates clarification response and resubmits escalation.
        - Writes immediate trace entries for CLARIFY, CLARIFICATION_ANSWER, and ESCALATION_RESUBMITTED.
        """
        # 1. Write immediate trace entry for CLARIFY request
        self.trace.record(
            node="human_gate",
            decision="CLARIFY",
            evidence=escalation.evidence,
            details={
                "escalation_id": escalation.escalation_id,
                "usubjid": escalation.usubjid,
                "code": escalation.code,
                "decision": "CLARIFY",
                "question": question,
            },
        )

        # 2. Answer question using real ATLAS/StudyGraph data
        answer_text, clarification_evidence = self._answer_clarification(
            escalation.usubjid, question
        )

        # 3. Write immediate trace entry for CLARIFICATION_ANSWER
        self.trace.record(
            node="human_gate",
            decision="CLARIFICATION_ANSWER",
            evidence=clarification_evidence,
            details={
                "escalation_id": escalation.escalation_id,
                "usubjid": escalation.usubjid,
                "code": escalation.code,
                "question": question,
                "answer": answer_text,
            },
        )

        # 4. Resubmit escalation with attached clarification data
        escalation.status = "RESUBMITTED"
        escalation.details["clarification_question"] = question
        escalation.details["clarification_answer"] = answer_text
        escalation.details["clarification_evidence"] = clarification_evidence

        # 5. Record in ReviewMemory
        clarification_data = {
            "question": question,
            "answer": answer_text,
            "evidence": clarification_evidence,
        }
        self.memory.record_escalation_decision(
            escalation_id=escalation.escalation_id,
            response="CLARIFY",
            clarification=clarification_data,
            usubjid=escalation.usubjid,
            code=escalation.code,
        )

        # 6. Write immediate trace entry for ESCALATION_RESUBMITTED
        combined_evidence = list(escalation.evidence)
        for ev in clarification_evidence:
            if ev not in combined_evidence:
                combined_evidence.append(ev)

        self.trace.record(
            node="human_gate",
            decision="ESCALATION_RESUBMITTED",
            evidence=combined_evidence,
            details={
                "escalation_id": escalation.escalation_id,
                "usubjid": escalation.usubjid,
                "code": escalation.code,
                "status": "RESUBMITTED",
                "clarification": clarification_data,
            },
        )

        return {
            "status": "RESUBMITTED",
            "escalation": escalation,
            "clarification_question": question,
            "clarification_answer": answer_text,
            "clarification_evidence": clarification_evidence,
            "evidence": combined_evidence,
        }

    # -------------------------------------------------------------------------
    # Clarification Engine (StudyGraph lookup without fabrication)
    # -------------------------------------------------------------------------
    def _answer_clarification(
        self,
        usubjid: Optional[str],
        question: str,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Answers factual clarification questions using real StudyGraph data.
        Returns: (answer_string, evidence_records)
        """
        if not usubjid or not self.atlas or not hasattr(self.atlas, "graph"):
            return "No subject record available in StudyGraph.", []

        p360 = self.atlas.graph.patient360(usubjid)
        if not p360:
            return f"Subject {usubjid} not found in StudyGraph.", []

        q_lower = question.lower()
        evidence: List[Dict[str, Any]] = []
        answer_parts: List[str] = []

        # 1. Answer screening/baseline ALT
        if "alt" in q_lower and ("screening" in q_lower or "baseline" in q_lower):
            screening_alt = None
            for lb in p360.get("labs", []):
                visit = (lb.get("VISIT") or "").upper().replace(" ", "")
                test = (lb.get("LBTESTCD") or "").upper()
                if test == "ALT" and visit in ["SCREENING", "DAY1", "BASELINE"]:
                    screening_alt = lb
                    break

            if screening_alt:
                val = screening_alt.get("LB_STD_VAL")
                unit = screening_alt.get("LB_STD_UNIT") or "U/L"
                seq = screening_alt.get("SEQ")
                val_str = f"{int(val)}" if (val is not None and val == int(val)) else f"{val}"
                answer_parts.append(f"screening ALT = {val_str} {unit}")
                if seq is not None:
                    evidence.append({"domain": "LB", "usubjid": usubjid, "seq": seq})
            else:
                answer_parts.append("no screening ALT recorded")

        # 2. Answer concomitant hepatotoxic medications
        if "concomitant" in q_lower or "hepatotoxic" in q_lower or "medication" in q_lower:
            cm_records = p360.get("concomitant_meds", []) or p360.get("concomitant_medications", [])
            hepatotoxic_meds = []
            known_hepatotoxic = [
                "acetaminophen", "paracetamol", "amiodarone", "methotrexate",
                "isoniazid", "ketoconazole", "steroid", "prednisone", "azathioprine"
            ]
            for cm in cm_records:
                trt = (cm.get("CMTRT") or "").lower()
                if any(h in trt for h in known_hepatotoxic):
                    hepatotoxic_meds.append(cm)
                    seq = cm.get("SEQ")
                    if seq is not None:
                        evidence.append({"domain": "CM", "usubjid": usubjid, "seq": seq})

            if hepatotoxic_meds:
                med_names = [m.get("CMTRT") for m in hepatotoxic_meds]
                answer_parts.append(f"concomitant hepatotoxic medication identified: {', '.join(med_names)}")
            else:
                answer_parts.append("no hepatotoxic concomitant medication")

        if not answer_parts:
            return "Subject records reviewed; no conflicting findings identified.", []

        full_answer = ", and ".join(answer_parts) + "."
        full_answer = full_answer[0].upper() + full_answer[1:]
        return full_answer, evidence

    # -------------------------------------------------------------------------
    # Monitoring Cycle Orchestration
    # -------------------------------------------------------------------------
    def process(
        self,
        escalations: List[Escalation],
        queries: List[Query],
        deviations: List[Deviation],
        cut: int,
    ) -> Dict[str, Any]:
        """
        Evaluates escalations, queries, and deviations through human gate rules
        during normal cycle execution.
        """
        approved_escalations: List[Escalation] = []
        approved_queries: List[Query] = []
        approved_deviations: List[Deviation] = []
        pending_review: List[Dict[str, Any]] = []

        # Triage Escalations
        for esc in escalations:
            # Check if already rejected in memory
            if self.memory.is_escalation_rejected(escalation_id=esc.escalation_id, usubjid=esc.usubjid, code=esc.code):
                continue

            if esc.status == "APPROVED" or self.memory.is_escalation_approved(escalation_id=esc.escalation_id, usubjid=esc.usubjid, code=esc.code):
                esc.status = "APPROVED"
                approved_escalations.append(esc)
            elif self.auto_approve_standard and esc.status != "REJECTED":
                esc.status = "APPROVED"
                approved_escalations.append(esc)
            else:
                # Pending human gate review
                pending_review.append({
                    "type": "ESCALATION",
                    "id": esc.escalation_id,
                    "code": esc.code,
                    "usubjid": esc.usubjid,
                    "reason": esc.summary or esc.details.get("rule", ""),
                    "urgency": esc.severity,
                    "status": esc.status,
                })

        # Standard clinical queries are dispatched for site resolution
        for q in queries:
            approved_queries.append(q)

        # Standard protocol deviations are logged
        for d in deviations:
            approved_deviations.append(d)

        decision_summary = {
            "cut": cut,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "approved_escalations_count": len(approved_escalations),
            "approved_queries_count": len(approved_queries),
            "approved_deviations_count": len(approved_deviations),
            "pending_review_count": len(pending_review),
            "status": "APPROVED" if not pending_review else "PENDING_HUMAN_REVIEW",
        }

        # Store in memory and log trace
        self.memory.record_human_decision(decision_summary)
        self.trace.record(
            node="human_gate",
            decision=decision_summary["status"],
            evidence=[],
            details=decision_summary,
        )

        return {
            "approved_escalations": approved_escalations,
            "approved_queries": approved_queries,
            "approved_deviations": approved_deviations,
            "pending_review": pending_review,
            "gate_decision": decision_summary,
        }
