"""
stage2/compliance.py

PS2 Compliance Node for Clinical Trial Protocol Adherence & Regulatory Monitoring.
Evaluates every subject against the protocol version in force at the requested data cut.

Responsibilities:
  1. Respects the requested protocol_version (v1, v2, v3) and mid-stage amendments.
  2. Evaluates every subject across all core compliance categories:
     - Visit Window violations (narrowed from ±7 days in v1 to ±3 days in v2/v3)
     - Prohibited Concomitant Medications (Glucocorticoids in v1-v3; Sulfonylureas in v3)
     - Eligibility violations (Age 18-75; HbA1c 7.0-10.5%)
     - Renal Exclusion violations (Screening Creatinine > 1.5 mg/dL, added in v2)
     - Dosing violations (Administered dose differs from protocol assigned dose)
  3. Preserves exact RecordRef evidence linking directly to StudyGraph records.
  4. Utilizes persistent ReviewMemory to suppress duplicate deviations on repeated cycles.
  5. Emits immediate, traceable decision records in TraceLog.
"""

from typing import List, Dict, Any, Optional
from stage2.models import Finding, Deviation
from stage2.trace import TraceLog
from stage2.memory import ReviewMemory
from stage1.atlas import Atlas
from stage1.study_graph import parse_date


class ComplianceNode:
    """
    Evaluates protocol adherence against active protocol versions and amendments.
    Produces subject-level Deviation records with exact StudyGraph evidence.
    """

    VISIT_TARGET_DAYS: Dict[str, int] = {
        "SCREENING": -14,
        "BASELINE": 0,
        "WEEK2": 14,
        "WEEK4": 28,
        "WEEK8": 56,
        "WEEK12": 84,
        "WEEK16": 112,
        "WEEK20": 140,
        "WEEK24": 168,
        "END OF STUDY": 182,
        "EOS": 182,
    }

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
    ) -> List[Deviation]:
        """
        Processes every subject against the requested protocol version in force at the cut.
        Emits new Deviations, suppresses duplicates via ReviewMemory, and writes trace entries.
        """
        # Ensure StudyGraph is built at the requested cut
        if self.atlas and hasattr(self.atlas, "graph"):
            if getattr(self.atlas.graph, "current_cut", None) != cut:
                self.atlas.graph.build(cut=cut)

        candidate_deviations: List[Deviation] = []

        # If Atlas is available, evaluate every subject in StudyGraph
        if self.atlas and hasattr(self.atlas, "graph") and self.atlas.graph.subjects:
            candidate_deviations.extend(
                self._evaluate_study_graph(cut=cut, protocol_version=protocol_version)
            )
        else:
            # Fallback for standalone evaluation of finding objects
            candidate_deviations.extend(
                self._evaluate_findings_fallback(findings, cut=cut, protocol_version=protocol_version)
            )

        # Apply Duplicate Suppression via ReviewMemory
        new_deviations: List[Deviation] = []
        suppressed_count = 0

        for dev in candidate_deviations:
            if self.memory.has_deviation(dev.deviation_id):
                suppressed_count += 1
                self.trace.record(
                    node="compliance",
                    decision="duplicate_deviation_suppressed",
                    evidence=dev.evidence,
                    details={
                        "deviation_id": dev.deviation_id,
                        "usubjid": dev.usubjid,
                        "category": dev.category,
                        "cut": cut,
                        "protocol_version": protocol_version,
                    },
                )
                continue

            # Record new deviation in memory and trace
            new_deviations.append(dev)
            self.memory.add_deviation(dev)
            if dev.usubjid:
                self.memory.flag_subject(dev.usubjid, f"PROTOCOL_DEVIATION_{dev.category}")
            if dev.site_id:
                self.memory.flag_site(dev.site_id, "SITE_DEVIATION_RATE")

            self.trace.record(
                node="compliance",
                decision="DEVIATION_LOGGED",
                evidence=dev.evidence,
                details={
                    "deviation_id": dev.deviation_id,
                    "usubjid": dev.usubjid,
                    "site": dev.site_id,
                    "category": dev.category,
                    "rule": dev.protocol_rule,
                    "cut": cut,
                    "protocol_version": protocol_version,
                },
            )

        # Category breakdown for summary trace
        category_breakdown: Dict[str, int] = {}
        for d in new_deviations:
            category_breakdown[d.category] = category_breakdown.get(d.category, 0) + 1

        # Emit COMPLIANCE_REVIEW_COMPLETE trace decision
        all_new_evidence = []
        for d in new_deviations:
            all_new_evidence.extend(d.evidence)

        self.trace.record(
            node="compliance",
            decision="COMPLIANCE_REVIEW_COMPLETE",
            evidence=all_new_evidence,
            details={
                "cut": cut,
                "protocol_version": protocol_version,
                "deviation_count": len(new_deviations),
                "category_breakdown": category_breakdown,
                "suppressed_count": suppressed_count,
                "total_active_in_memory": len(self.memory.get_all_deviations()),
            },
        )

        return new_deviations

    # -------------------------------------------------------------------------
    # Core Evaluation Logic Across StudyGraph
    # -------------------------------------------------------------------------
    def _evaluate_study_graph(self, cut: int, protocol_version: int) -> List[Deviation]:
        """
        Evaluates every subject in StudyGraph according to the rules of protocol_version.
        """
        deviations: List[Deviation] = []

        # Rule parameters determined by protocol_version
        # Protocol §4: Visit window narrowed from ±7 days (v1) to ±3 days (v2, v3)
        window_days = 7 if protocol_version == 1 else 3

        # Protocol §3: Renal exclusion active in v2 and v3, inactive in v1
        renal_rule_active = protocol_version >= 2

        # Protocol §5: Sulfonylurea prohibited starting in v3; Glucocorticoids in v1-v3
        prohibit_sulfonylurea = protocol_version >= 3

        for u, p360 in sorted(self.atlas.graph.subjects.items()):
            site_id = p360.get("site_id") or (u.split("-")[1] if "-" in u else "UNKNOWN")
            dm = p360.get("demographics")

            # -----------------------------------------------------------------
            # 1. Visit Window Violations (Protocol §4)
            # -----------------------------------------------------------------
            base_dt = None
            if dm:
                base_dt = dm.get("RFSTDTC_PARSED") or parse_date(dm.get("RFSTDTC"))

            if base_dt:
                # Group vitals visits to evaluate distinct visit dates per subject
                subj_visits: Dict[str, Any] = {}
                for r in p360.get("vitals", []):
                    vis = r.get("VISIT", "").strip().upper()
                    dt = r.get("VSDTC_PARSED") or parse_date(r.get("VSDTC"))
                    seq = r.get("SEQ")
                    if vis and dt and vis not in subj_visits:
                        subj_visits[vis] = (dt, seq, r.get("VSDTC"))

                for vis, (vis_dt, seq, dtc_raw) in sorted(subj_visits.items()):
                    vis_clean = vis.replace(" ", "")
                    target_day = self.VISIT_TARGET_DAYS.get(vis_clean) or self.VISIT_TARGET_DAYS.get(vis)
                    if target_day is None:
                        continue

                    actual_day = (vis_dt - base_dt).days
                    deviation_days = abs(actual_day - target_day)

                    if deviation_days > window_days:
                        dev_id = f"DEV-VISIT_WINDOW-{u}-{vis_clean}-V{protocol_version}"
                        rule_desc = f"Protocol v{protocol_version} §4 Visit Window: Day {target_day} ± {window_days} days"
                        desc = (
                            f"Subject {u} attended {vis} on {dtc_raw} (Day {actual_day}), "
                            f"exceeding allowable protocol window of Day {target_day} ± {window_days} days "
                            f"(variance: {deviation_days} days)."
                        )
                        ref_dict = {"domain": "VS", "usubjid": u, "seq": seq}
                        deviations.append(
                            Deviation(
                                deviation_id=dev_id,
                                category="VISIT_WINDOW",
                                usubjid=u,
                                site_id=site_id,
                                protocol_rule=rule_desc,
                                description=desc,
                                severity="MAJOR",
                                cut=cut,
                                protocol_version=protocol_version,
                                evidence=[ref_dict],
                                details={
                                    "visit": vis,
                                    "target_day": target_day,
                                    "actual_day": actual_day,
                                    "variance_days": deviation_days,
                                    "window_days": window_days,
                                    "key": vis_clean,
                                },
                            )
                        )

            # -----------------------------------------------------------------
            # 2. Prohibited Concomitant Medications (Protocol §5)
            # -----------------------------------------------------------------
            for cm in p360.get("medications", []):
                clas = cm.get("CMCLAS", "").upper()
                trt = cm.get("CMTRT", "").upper()
                seq = cm.get("SEQ")

                is_gluco = "GLUCOCORTICOID" in clas or "GLUCOCORTICOID" in trt
                is_sulfo = "SULFONYLUREA" in clas or "SULFONYLUREA" in trt

                if is_gluco or (prohibit_sulfonylurea and is_sulfo):
                    med_type = "Systemic Glucocorticoid" if is_gluco else "Sulfonylurea"
                    med_name = cm.get("CMTRT", med_type)
                    dev_id = f"DEV-PROHIBITED_MED-{u}-{seq}-V{protocol_version}"
                    rule_desc = f"Protocol v{protocol_version} §5 Prohibited Concomitant Medications: {med_type}"
                    desc = (
                        f"Subject {u} received prohibited concomitant medication: {med_name} "
                        f"({med_type}) under Protocol v{protocol_version} §5."
                    )
                    ref_dict = {"domain": "CM", "usubjid": u, "seq": seq}
                    deviations.append(
                        Deviation(
                            deviation_id=dev_id,
                            category="PROHIBITED_MED",
                            usubjid=u,
                            site_id=site_id,
                            protocol_rule=rule_desc,
                            description=desc,
                            severity="MAJOR",
                            cut=cut,
                            protocol_version=protocol_version,
                            evidence=[ref_dict],
                            details={
                                "medication": med_name,
                                "class": clas,
                                "med_type": med_type,
                                "seq": seq,
                                "key": seq,
                            },
                        )
                    )

            # -----------------------------------------------------------------
            # 3. Eligibility Violations (Protocol §2 & §3)
            # -----------------------------------------------------------------
            if dm:
                dm_seq = dm.get("SEQ")
                # Age 18–75 at screening
                if dm.get("AGE"):
                    try:
                        age = float(dm["AGE"])
                        if age < 18 or age > 75:
                            dev_id = f"DEV-ELIGIBILITY-{u}-AGE-V{protocol_version}"
                            rule_desc = f"Protocol v{protocol_version} §2 Inclusion Criteria: Age 18–75 years"
                            desc = (
                                f"Subject {u} was enrolled with age {int(age)}, violating Protocol §2 "
                                f"inclusion criteria (allowable age range: 18 to 75 years)."
                            )
                            ref_dict = {"domain": "DM", "usubjid": u}
                            if dm_seq is not None:
                                ref_dict["seq"] = dm_seq
                            deviations.append(
                                Deviation(
                                    deviation_id=dev_id,
                                    category="ELIGIBILITY",
                                    usubjid=u,
                                    site_id=site_id,
                                    protocol_rule=rule_desc,
                                    description=desc,
                                    severity="CRITICAL",
                                    cut=cut,
                                    protocol_version=protocol_version,
                                    evidence=[ref_dict],
                                    details={"criterion": "AGE", "val": age, "key": "AGE"},
                                )
                            )
                    except (ValueError, TypeError):
                        pass

                # Screening HbA1c 7.0%–10.5%
                if dm.get("SCR_HBA1C"):
                    try:
                        hba1c = float(dm["SCR_HBA1C"])
                        if hba1c < 7.0 or hba1c > 10.5:
                            dev_id = f"DEV-ELIGIBILITY-{u}-HBA1C-V{protocol_version}"
                            rule_desc = f"Protocol v{protocol_version} §2 Inclusion Criteria: HbA1c 7.0%–10.5%"
                            desc = (
                                f"Subject {u} was enrolled with screening HbA1c of {hba1c}%, violating Protocol §2 "
                                f"inclusion criteria (allowable HbA1c range: 7.0% to 10.5%)."
                            )
                            ref_dict = {"domain": "DM", "usubjid": u}
                            if dm_seq is not None:
                                ref_dict["seq"] = dm_seq
                            deviations.append(
                                Deviation(
                                    deviation_id=dev_id,
                                    category="ELIGIBILITY",
                                    usubjid=u,
                                    site_id=site_id,
                                    protocol_rule=rule_desc,
                                    description=desc,
                                    severity="CRITICAL",
                                    cut=cut,
                                    protocol_version=protocol_version,
                                    evidence=[ref_dict],
                                    details={"criterion": "HBA1C", "val": hba1c, "key": "HBA1C"},
                                )
                            )
                    except (ValueError, TypeError):
                        pass

            # -----------------------------------------------------------------
            # 4. Renal Exclusion Violations (Protocol §3, Added in Amendment 2)
            # -----------------------------------------------------------------
            if renal_rule_active:
                for lb in p360.get("labs", []):
                    if lb.get("LBTESTCD") == "CREAT" and lb.get("VISIT") == "SCREENING":
                        val = lb.get("LB_STD_VAL")
                        seq = lb.get("SEQ")
                        if val is not None and val > 1.5:
                            dev_id = f"DEV-RENAL_EXCLUSION-{u}-V{protocol_version}"
                            rule_desc = (
                                f"Protocol v{protocol_version} §3 Exclusion Criteria: "
                                "Creatinine > 1.5 mg/dL at screening (Amendment 2)"
                            )
                            desc = (
                                f"Subject {u} had screening creatinine of {val:.2f} mg/dL (> 1.5 mg/dL), "
                                f"violating Protocol v{protocol_version} §3 renal exclusion criteria."
                            )
                            ref_dict = {"domain": "LB", "usubjid": u, "seq": seq}
                            deviations.append(
                                Deviation(
                                    deviation_id=dev_id,
                                    category="RENAL_EXCLUSION",
                                    usubjid=u,
                                    site_id=site_id,
                                    protocol_rule=rule_desc,
                                    description=desc,
                                    severity="CRITICAL",
                                    cut=cut,
                                    protocol_version=protocol_version,
                                    evidence=[ref_dict],
                                    details={"test": "CREAT", "value": val, "threshold": 1.5, "key": "RENAL"},
                                )
                            )

            # -----------------------------------------------------------------
            # 5. Dosing Deviations (Protocol §8)
            # -----------------------------------------------------------------
            arm = dm.get("ARM", "UNKNOWN") if dm else "UNKNOWN"
            expected_dose = 10.0 if arm == "DRUG" else 0.0

            for ex in p360.get("exposure", []):
                dose = ex.get("EXDOSE_NUM")
                seq = ex.get("SEQ")
                if dose is not None and dose != expected_dose:
                    dev_id = f"DEV-DOSING-{u}-{seq}-V{protocol_version}"
                    rule_desc = f"Protocol v{protocol_version} §8 Dosing: {expected_dose} mg daily for {arm}"
                    desc = (
                        f"Subject {u} received dose of {dose} mg (expected {expected_dose} mg for {arm} arm), "
                        f"violating Protocol v{protocol_version} §8 dosing specification."
                    )
                    ref_dict = {"domain": "EX", "usubjid": u, "seq": seq}
                    deviations.append(
                        Deviation(
                            deviation_id=dev_id,
                            category="DOSING",
                            usubjid=u,
                            site_id=site_id,
                            protocol_rule=rule_desc,
                            description=desc,
                            severity="MAJOR",
                            cut=cut,
                            protocol_version=protocol_version,
                            evidence=[ref_dict],
                            details={
                                "administered_dose": dose,
                                "expected_dose": expected_dose,
                                "arm": arm,
                                "seq": seq,
                                "key": seq,
                            },
                        )
                    )

        return deviations

    # -------------------------------------------------------------------------
    # Fallback Evaluator (when findings are provided without full Atlas)
    # -------------------------------------------------------------------------
    def _evaluate_findings_fallback(
        self,
        findings: List[Finding],
        cut: int,
        protocol_version: int,
    ) -> List[Deviation]:
        """
        Fallback evaluator converting finding objects into deviations if StudyGraph is unavailable.
        """
        deviations: List[Deviation] = []
        for f in findings:
            if f.category in ["PROTOCOL", "VISIT_WINDOW", "DOSING_DEVIATION", "DOSING", "ELIGIBILITY"]:
                cat = "PROHIBITED_MED" if f.code == "PROHIBITED_MED" else f.category
                dev_id = f"DEV-{cat}-{f.usubjid}-{f.finding_id}-V{protocol_version}"
                deviations.append(
                    Deviation(
                        deviation_id=dev_id,
                        category=cat,
                        usubjid=f.usubjid,
                        site_id=f.site_id,
                        protocol_rule=f.details.get("rule", f"Protocol v{protocol_version} compliance specification"),
                        description=f.description,
                        severity="CRITICAL" if f.severity == "CRITICAL" else "MAJOR",
                        cut=cut,
                        protocol_version=protocol_version,
                        evidence=f.evidence,
                        details={"cut": cut, "protocol_version": protocol_version, "finding_id": f.finding_id},
                    )
                )
        return deviations
