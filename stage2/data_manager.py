"""
stage2/data_manager.py

Data Manager Node for Problem Statement 2 — MONITOR.
Handles clinical data quality, discrepancy identification, and query generation.

Rules implemented:
  RULE 1 — Dosing Discrepancy Querying (WRONG_DOSE -> EX.EXDOSE query)
  RULE 2 — AE Seriousness Coding Querying (AESHOSP=Y and AESER=N -> AE.AESER query)
  RULE 3 — Non-Query Findings & Selective Triage (Compliance/Safety/Disposition -> no_query_needed)
  RULE 4 — Duplicate Query Suppression (Consult ReviewMemory to prevent re-querying across cycles)
  RULE 5 — Evidence Integrity (Preserve Finding evidence exactly without manual fabrication)
  RULE 6 — Immediate Decision Tracing (query_generated, no_query_needed, duplicate_query_suppressed)
"""

from typing import List, Dict, Any, Optional, Tuple
from stage2.models import Finding, Query
from stage2.trace import TraceLog
from stage2.memory import ReviewMemory
from stage1.atlas import Atlas


class DataManagerNode:
    """
    Evaluates clinical data consistency, missing entries, and discrepancies.
    Generates formal Query records for site clarification.
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
    ) -> List[Query]:
        """
        Processes candidate findings and produces verified data-management queries.
        """
        queries: List[Query] = []

        if not findings:
            self.trace.record(
                node="data_manager",
                decision="no_findings_to_evaluate",
                evidence=[],
                details={"cut": cut, "protocol_version": protocol_version, "query_count": 0},
            )
            return queries

        for f in findings:
            # -----------------------------------------------------------------
            # 1. Dosing Discrepancies (RULE 1)
            # -----------------------------------------------------------------
            if f.code == "WRONG_DOSE" or f.category == "DOSING":
                domain = "EX"
                target_field = "EXDOSE"
                query_text = (
                    f"Dosing discrepancy for Subject {f.usubjid}: "
                    "Administered dose deviates from protocol-assigned cohort dose. "
                    "Please confirm administered dose (EXDOSE), infusion duration, and provide explanation for deviation."
                )

                # Check duplicate (RULE 4)
                if self._is_duplicate_query(f.usubjid, domain, target_field):
                    self.trace.record(
                        node="data_manager",
                        decision="duplicate_query_suppressed",
                        evidence=f.evidence,
                        details={
                            "finding_id": f.finding_id,
                            "usubjid": f.usubjid,
                            "domain": domain,
                            "target_field": target_field,
                            "reason": f"Query on {domain}.{target_field} for {f.usubjid} already exists in ReviewMemory; duplicate suppressed.",
                            "cut": cut,
                        },
                    )
                    continue

                qry_id = f"QRY-EXDOSE-{f.usubjid}-CUT{cut}"
                qry = Query(
                    query_id=qry_id,
                    finding_id=f.finding_id,
                    usubjid=f.usubjid,
                    site_id=f.site_id,
                    domain=domain,
                    target_field=target_field,
                    query_text=query_text,
                    status="OPEN",
                    evidence=f.evidence,  # RULE 5: Preserve exact evidence
                    details={
                        "rule": "Protocol §8 Exposure and Dosing",
                        "cut": cut,
                        "protocol_version": protocol_version,
                        "severity": f.severity,
                    },
                )
                queries.append(qry)
                self.memory.add_query(qry)
                if f.usubjid:
                    self.memory.flag_subject(f.usubjid, f"OPEN_QUERY_{domain}")
                if f.site_id:
                    self.memory.flag_site(f.site_id, "SITE_OPEN_QUERIES")

                # RULE 6: Immediate decision tracing
                self.trace.record(
                    node="data_manager",
                    decision="query_generated",
                    evidence=f.evidence,
                    details={
                        "query_id": qry_id,
                        "usubjid": f.usubjid,
                        "site_id": f.site_id,
                        "domain": domain,
                        "target_field": target_field,
                        "query_text": query_text,
                    },
                )
                continue

            # -----------------------------------------------------------------
            # 2. Adverse Event Seriousness Miscoding Discrepancy (RULE 2)
            # -----------------------------------------------------------------
            if f.code == "SERIOUS_AE" or (f.category == "SAFETY" and any(e.get("domain") == "AE" for e in f.evidence)):
                if self._check_ae_miscoding(f):
                    domain = "AE"
                    target_field = "AESER"
                    query_text = (
                        f"Adverse event discrepancy for Subject {f.usubjid}: "
                        "Subject was hospitalized (AESHOSP='Y') but event is recorded as non-serious (AESER='N'). "
                        "Per Protocol §6, hospitalization fulfills serious adverse event criteria. "
                        "Please update AESER to 'Y' or clarify if hospitalization was pre-planned/elective."
                    )

                    # Check duplicate (RULE 4)
                    if self._is_duplicate_query(f.usubjid, domain, target_field):
                        self.trace.record(
                            node="data_manager",
                            decision="duplicate_query_suppressed",
                            evidence=f.evidence,
                            details={
                                "finding_id": f.finding_id,
                                "usubjid": f.usubjid,
                                "domain": domain,
                                "target_field": target_field,
                                "reason": f"Query on {domain}.{target_field} for {f.usubjid} already exists in ReviewMemory; duplicate suppressed.",
                                "cut": cut,
                            },
                        )
                        continue

                    qry_id = f"QRY-AESER-{f.usubjid}-CUT{cut}"
                    qry = Query(
                        query_id=qry_id,
                        finding_id=f.finding_id,
                        usubjid=f.usubjid,
                        site_id=f.site_id,
                        domain=domain,
                        target_field=target_field,
                        query_text=query_text,
                        status="OPEN",
                        evidence=f.evidence,  # RULE 5: Preserve exact evidence
                        details={
                            "rule": "Protocol §6 Serious Adverse Event Criteria",
                            "cut": cut,
                            "protocol_version": protocol_version,
                            "severity": "HIGH",
                        },
                    )
                    queries.append(qry)
                    self.memory.add_query(qry)
                    if f.usubjid:
                        self.memory.flag_subject(f.usubjid, f"OPEN_QUERY_{domain}")
                    if f.site_id:
                        self.memory.flag_site(f.site_id, "SITE_OPEN_QUERIES")

                    # RULE 6: Immediate decision tracing
                    self.trace.record(
                        node="data_manager",
                        decision="query_generated",
                        evidence=f.evidence,
                        details={
                            "query_id": qry_id,
                            "usubjid": f.usubjid,
                            "site_id": f.site_id,
                            "domain": domain,
                            "target_field": target_field,
                            "query_text": query_text,
                        },
                    )
                    continue
                else:
                    # Correctly coded serious AE; handled by Medical Monitor
                    reason = "Serious AE is correctly coded (AESER='Y'); escalated to Medical Monitor, no CRF data query required."
                    self.trace.record(
                        node="data_manager",
                        decision="no_query_needed",
                        evidence=f.evidence,
                        details={
                            "finding_id": f.finding_id,
                            "code": f.code,
                            "usubjid": f.usubjid,
                            "reason": reason,
                            "cut": cut,
                        },
                    )
                    continue

            # -----------------------------------------------------------------
            # 3. Non-Query Findings (RULE 3)
            # -----------------------------------------------------------------
            reason = self._get_non_query_reason(f)
            self.trace.record(
                node="data_manager",
                decision="no_query_needed",
                evidence=f.evidence,
                details={
                    "finding_id": f.finding_id,
                    "code": f.code,
                    "category": f.category,
                    "usubjid": f.usubjid,
                    "reason": reason,
                    "cut": cut,
                },
            )

        return queries

    # -------------------------------------------------------------------------
    # Helper Evaluators
    # -------------------------------------------------------------------------
    def _is_duplicate_query(self, usubjid: Optional[str], domain: str, target_field: str) -> bool:
        """
        RULE 4: Checks ReviewMemory to determine if a query for this subject, domain,
        and target field already exists.
        """
        if not usubjid:
            return False

        for existing_qry in self.memory.get_all_queries():
            if existing_qry.usubjid == usubjid and existing_qry.domain == domain and existing_qry.target_field == target_field:
                return True
        return False

    def _check_ae_miscoding(self, f: Finding) -> bool:
        """
        Checks if the AE finding corresponds to an AESHOSP='Y' and AESER!='Y' discrepancy.
        """
        if f.code == "SAE_MISCODED":
            return True

        if self.atlas and hasattr(self.atlas, "graph") and self.atlas.graph.subjects:
            p360 = self.atlas.graph.subjects.get(f.usubjid)
            if p360:
                for r in p360.get("adverse_events", []):
                    hosp = (r.get("AESHOSP") or "").upper()
                    ser = (r.get("AESER") or "").upper()
                    matching_seq = any(
                        str(ev.get("seq") or ev.get("SEQ")) == str(r.get("SEQ"))
                        for ev in f.evidence
                    ) or not f.evidence
                    if matching_seq and hosp == "Y" and ser != "Y":
                        return True
        return False

    def _get_non_query_reason(self, f: Finding) -> str:
        """
        RULE 3: Returns clinical reasoning why a finding does not require a site query.
        """
        if f.code == "HYS_LAW":
            return "Potential Hy's Law acute hepatotoxicity signal handled via Medical Monitor escalation; routine CRF data query not indicated."
        elif f.code == "PROHIBITED_MED" or f.category == "PROTOCOL":
            return "Concomitant medication protocol deviation tracked by Compliance Node; no CRF data discrepancy query required."
        elif f.code == "AE_DISCONTINUATION" or f.category == "DISPOSITION":
            return "Routine study discontinuation documented in disposition domain; no CRF data discrepancy query required."
        return f"Non-query observation ({f.code}); no site query indicated."
