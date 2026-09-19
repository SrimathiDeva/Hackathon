"""
stage2/models.py

Data models for Problem Statement 2 — MONITOR.
Defines core dataclasses:
  - Finding
  - Query
  - Escalation
  - Deviation
  - ReviewReport
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone


@dataclass
class Finding:
    """
    Represents a clinical, safety, laboratory, or operational finding
    detected by the monitoring system.
    """
    finding_id: str
    category: str  # SAFETY | DOSING | LAB | DISPOSITION | PROTOCOL | DATA_QUALITY
    code: str = ""  # HYS_LAW | WRONG_DOSE | PROHIBITED_MED | SERIOUS_AE | AE_DISCONTINUATION
    usubjid: Optional[str] = None
    site_id: Optional[str] = None
    description: str = ""
    rationale: str = ""
    severity: str = "MEDIUM"  # LOW | MEDIUM | HIGH | CRITICAL
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def site(self) -> Optional[str]:
        return self.site_id

    @site.setter
    def site(self, val: Optional[str]) -> None:
        self.site_id = val

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["site"] = self.site_id
        return d


@dataclass
class Query:
    """
    Represents a clinical or data-management query raised for a site or investigator.
    """
    query_id: str
    finding_id: Optional[str] = None
    usubjid: Optional[str] = None
    site_id: Optional[str] = None
    domain: str = ""
    target_field: str = ""
    query_text: str = ""
    status: str = "OPEN"  # OPEN | ANSWERED | CLOSED | CANCELLED
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    response: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Escalation:
    """
    Represents a clinical safety or trial conduct escalation requiring
    urgent review by the Medical Monitor.
    """
    escalation_id: str
    code: str = ""
    finding_id: Optional[str] = None
    usubjid: Optional[str] = None
    site_id: Optional[str] = None
    severity: str = "HIGH"  # LOW | MEDIUM | HIGH | CRITICAL
    summary: str = ""
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    alternatives: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    escalated_to: str = "MEDICAL_MONITOR"
    status: str = "PENDING"  # PENDING | ACKNOWLEDGED | RESOLVED
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def urgency(self) -> str:
        return self.severity

    @urgency.setter
    def urgency(self, val: str) -> None:
        self.severity = val

    @property
    def reason(self) -> str:
        return self.summary

    @reason.setter
    def reason(self, val: str) -> None:
        self.summary = val

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["urgency"] = self.severity
        d["reason"] = self.summary
        return d


@dataclass
class Deviation:
    """
    Represents a protocol deviation (e.g. visit window, dosing, inclusion/exclusion).
    """
    deviation_id: str
    category: str  # VISIT_WINDOW | DOSING | ELIGIBILITY | PROCEDURE | PROHIBITED_MED | RENAL_EXCLUSION
    usubjid: Optional[str] = None
    site_id: Optional[str] = None
    protocol_rule: str = ""
    description: str = ""
    severity: str = "MAJOR"  # MINOR | MAJOR | CRITICAL
    cut: Optional[int] = None
    protocol_version: Optional[int] = None
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def site(self) -> Optional[str]:
        return self.site_id

    @site.setter
    def site(self, val: Optional[str]) -> None:
        self.site_id = val

    @property
    def explanation(self) -> str:
        return self.description

    @explanation.setter
    def explanation(self, val: str) -> None:
        self.description = val

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["site"] = self.site_id
        d["explanation"] = self.description
        d["cut"] = self.cut
        d["protocol_version"] = self.protocol_version
        return d



@dataclass
class ReviewReport:
    """
    Comprehensive summary report produced by ReviewCrew at the completion of a monitoring cycle.
    """
    cycle_id: str
    cut: int
    protocol_version: int
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    findings: List[Finding] = field(default_factory=list)
    queries: List[Query] = field(default_factory=list)
    escalations: List[Escalation] = field(default_factory=list)
    deviations: List[Deviation] = field(default_factory=list)
    actions_executed: List[Dict[str, Any]] = field(default_factory=list)
    trace_summary: Dict[str, Any] = field(default_factory=dict)
    status: str = "COMPLETED"  # COMPLETED | FAILED | PENDING_REVIEW

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "cut": self.cut,
            "protocol_version": self.protocol_version,
            "timestamp": self.timestamp,
            "findings": [f.to_dict() if hasattr(f, "to_dict") else f for f in self.findings],
            "queries": [q.to_dict() if hasattr(q, "to_dict") else q for q in self.queries],
            "escalations": [e.to_dict() if hasattr(e, "to_dict") else e for e in self.escalations],
            "deviations": [d.to_dict() if hasattr(d, "to_dict") else d for d in self.deviations],
            "actions_executed": self.actions_executed,
            "trace_summary": self.trace_summary,
            "status": self.status,
        }
