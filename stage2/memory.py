"""
stage2/memory.py

Persistent memory storage for Problem Statement 2 — MONITOR.
Maintains state across review cycles for:
  - previously raised queries
  - previously made escalations
  - human decisions
  - subject flags
  - site flags
"""

import json
import os
from typing import Dict, List, Any, Optional
from stage2.models import Query, Escalation, Deviation


class ReviewMemory:
    """
    State repository for clinical review operations.
    Prevents duplicate queries/escalations and tracks cumulative human oversight.
    """

    def __init__(self, persistence_path: Optional[str] = None):
        self.persistence_path = persistence_path
        self.queries: Dict[str, Query] = {}
        self.escalations: Dict[str, Escalation] = {}
        self.deviations: Dict[str, Deviation] = {}
        self.human_decisions: List[Dict[str, Any]] = []
        self.subject_flags: Dict[str, List[str]] = {}
        self.site_flags: Dict[str, List[str]] = {}

        if self.persistence_path and os.path.exists(self.persistence_path):
            self.load(self.persistence_path)

    # -------------------------------------------------------------------------
    # Deviations
    # -------------------------------------------------------------------------
    def add_deviation(self, deviation: Deviation) -> None:
        """Stores a protocol deviation."""
        self.deviations[deviation.deviation_id] = deviation

    def has_deviation(self, deviation_id: str) -> bool:
        """Checks if a deviation with this ID already exists."""
        return deviation_id in self.deviations

    def get_deviation(self, deviation_id: str) -> Optional[Deviation]:
        """Retrieves a deviation by ID."""
        return self.deviations.get(deviation_id)

    def get_all_deviations(self) -> List[Deviation]:
        """Returns all stored deviations."""
        return list(self.deviations.values())

    def is_duplicate_deviation(
        self,
        usubjid: Optional[str] = None,
        category: Optional[str] = None,
        key: Optional[str] = None,
        protocol_version: Optional[int] = None,
    ) -> bool:
        """Checks if a matching deviation has already been logged."""
        for d in self.deviations.values():
            if usubjid and d.usubjid != usubjid:
                continue
            if category and d.category != category:
                continue
            if protocol_version is not None and d.protocol_version is not None:
                if d.protocol_version != protocol_version:
                    continue
            if key is not None:
                d_key = d.details.get("key") or d.details.get("visit") or d.details.get("seq")
                if str(d_key) == str(key):
                    return True
            else:
                return True
        return False


    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------
    def add_query(self, query: Query) -> None:
        """Stores a raised query."""
        self.queries[query.query_id] = query

    def has_query(self, query_id: str) -> bool:
        """Checks if a query with this ID already exists."""
        return query_id in self.queries

    def get_query(self, query_id: str) -> Optional[Query]:
        """Retrieves a query by ID."""
        return self.queries.get(query_id)

    def get_all_queries(self) -> List[Query]:
        """Returns all stored queries."""
        return list(self.queries.values())

    # -------------------------------------------------------------------------
    # Escalations
    # -------------------------------------------------------------------------
    def add_escalation(self, escalation: Escalation) -> None:
        """Stores an escalation."""
        self.escalations[escalation.escalation_id] = escalation

    def has_escalation(self, escalation_id: str) -> bool:
        """Checks if an escalation with this ID already exists."""
        return escalation_id in self.escalations

    def get_escalation(self, escalation_id: str) -> Optional[Escalation]:
        """Retrieves an escalation by ID."""
        return self.escalations.get(escalation_id)

    def get_all_escalations(self) -> List[Escalation]:
        """Returns all stored escalations."""
        return list(self.escalations.values())

    # -------------------------------------------------------------------------
    # Human Decisions & Escalation Lifecycle
    # -------------------------------------------------------------------------
    def record_human_decision(self, decision: Dict[str, Any]) -> None:
        """Records a human gate decision."""
        self.human_decisions.append(decision)

    def get_human_decisions(self) -> List[Dict[str, Any]]:
        """Returns all human gate decisions."""
        return list(self.human_decisions)

    def record_escalation_decision(
        self,
        escalation_id: str,
        response: str,
        reason: Optional[str] = None,
        clarification: Optional[Dict[str, Any]] = None,
        usubjid: Optional[str] = None,
        code: Optional[str] = None,
    ) -> None:
        """
        Stores the human monitor decision for an escalation:
        APPROVED, REJECTED, or CLARIFY.
        """
        from datetime import datetime, timezone
        decision_record = {
            "escalation_id": escalation_id,
            "response": response,
            "reason": reason,
            "clarification": clarification,
            "usubjid": usubjid,
            "code": code,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.human_decisions.append(decision_record)

        # Update stored escalation in memory if present
        if escalation_id in self.escalations:
            esc = self.escalations[escalation_id]
            if response == "CLARIFY":
                esc.status = "RESUBMITTED"
            else:
                esc.status = response
            if reason:
                esc.details["rejection_reason"] = reason
            if clarification:
                esc.details["clarification"] = clarification

    def get_escalation_decision(self, escalation_id: str) -> Optional[Dict[str, Any]]:
        """Returns the most recent decision record for an escalation ID."""
        for d in reversed(self.human_decisions):
            if d.get("escalation_id") == escalation_id:
                return d
        return None

    def is_escalation_rejected(
        self,
        escalation_id: Optional[str] = None,
        usubjid: Optional[str] = None,
        code: Optional[str] = None,
    ) -> bool:
        """Checks if an escalation was rejected previously."""
        for d in self.human_decisions:
            if d.get("response") == "REJECTED":
                if escalation_id and d.get("escalation_id") == escalation_id:
                    return True
                if usubjid and d.get("usubjid") == usubjid:
                    if code is None or d.get("code") == code:
                        return True
        return False

    def is_escalation_approved(
        self,
        escalation_id: Optional[str] = None,
        usubjid: Optional[str] = None,
        code: Optional[str] = None,
    ) -> bool:
        """Checks if an escalation was approved previously."""
        for d in self.human_decisions:
            if d.get("response") == "APPROVED":
                if escalation_id and d.get("escalation_id") == escalation_id:
                    return True
                if usubjid and d.get("usubjid") == usubjid:
                    if code is None or d.get("code") == code:
                        return True
        return False

    # -------------------------------------------------------------------------
    # Subject & Site Flags
    # -------------------------------------------------------------------------
    def flag_subject(self, usubjid: str, flag: str) -> None:
        """Adds a monitoring flag to a subject."""
        if usubjid not in self.subject_flags:
            self.subject_flags[usubjid] = []
        if flag not in self.subject_flags[usubjid]:
            self.subject_flags[usubjid].append(flag)

    def get_subject_flags(self, usubjid: str) -> List[str]:
        """Retrieves all flags associated with a subject."""
        return list(self.subject_flags.get(usubjid, []))

    def flag_site(self, site_id: str, flag: str) -> None:
        """Adds an operational flag to a site."""
        if site_id not in self.site_flags:
            self.site_flags[site_id] = []
        if flag not in self.site_flags[site_id]:
            self.site_flags[site_id].append(flag)

    def get_site_flags(self, site_id: str) -> List[str]:
        """Retrieves all flags associated with a site."""
        return list(self.site_flags.get(site_id, []))

    # -------------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        """Exports state to dictionary."""
        return {
            "queries": {k: q.to_dict() for k, q in self.queries.items()},
            "escalations": {k: e.to_dict() for k, e in self.escalations.items()},
            "deviations": {k: d.to_dict() for k, d in self.deviations.items()},
            "human_decisions": self.human_decisions,
            "subject_flags": self.subject_flags,
            "site_flags": self.site_flags,
        }

    def save(self, path: Optional[str] = None) -> None:
        """Saves current state to JSON file."""
        target_path = path or self.persistence_path
        if not target_path:
            return
        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    def load(self, path: str) -> None:
        """Loads state from JSON file."""
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.queries.clear()
        for k, qd in data.get("queries", {}).items():
            self.queries[k] = Query(**qd)

        self.escalations.clear()
        for k, ed in data.get("escalations", {}).items():
            clean_ed = dict(ed)
            if "urgency" in clean_ed and "severity" not in clean_ed:
                clean_ed["severity"] = clean_ed.pop("urgency")
            else:
                clean_ed.pop("urgency", None)
            if "reason" in clean_ed and "summary" not in clean_ed:
                clean_ed["summary"] = clean_ed.pop("reason")
            else:
                clean_ed.pop("reason", None)
            self.escalations[k] = Escalation(**clean_ed)

        self.deviations.clear()
        for k, dd in data.get("deviations", {}).items():
            clean_dd = dict(dd)
            clean_dd.pop("site", None)
            clean_dd.pop("explanation", None)
            self.deviations[k] = Deviation(**clean_dd)

        self.human_decisions = list(data.get("human_decisions", []))
        self.subject_flags = {k: list(v) for k, v in data.get("subject_flags", {}).items()}
        self.site_flags = {k: list(v) for k, v in data.get("site_flags", {}).items()}

