"""
stage2/trace.py

Audit logging and decision tracing for Problem Statement 2 — MONITOR.
Records every node decision immediately with timestamp, node, decision, evidence, and details.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone


@dataclass
class TraceEntry:
    """
    Individual trace record capturing a specific decision made by an agent node.
    """
    timestamp: str
    node: str
    decision: str
    evidence: List[Any] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "node": self.node,
            "decision": self.decision,
            "evidence": self.evidence,
            "details": self.details,
        }


class TraceLog:
    """
    Append-only trace logger recording all decisions made by ReviewCrew nodes.
    Ensures complete provenance, transparency, and audit compliance.
    """

    def __init__(self):
        self.entries: List[TraceEntry] = []

    def record(
        self,
        node: str,
        decision: str,
        evidence: Optional[List[Any]] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> TraceEntry:
        """
        Records a node decision immediately and returns the created TraceEntry.
        """
        entry = TraceEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            node=node,
            decision=decision,
            evidence=evidence if evidence is not None else [],
            details=details if details is not None else {},
        )
        self.entries.append(entry)
        return entry

    def get_entries(self) -> List[TraceEntry]:
        """Returns all logged trace entries."""
        return list(self.entries)

    def get_by_node(self, node: str) -> List[TraceEntry]:
        """Filters trace entries by node name."""
        return [e for e in self.entries if e.node.lower() == node.lower()]

    def clear(self) -> None:
        """Clears all entries in the trace log."""
        self.entries.clear()

    def to_list(self) -> List[Dict[str, Any]]:
        """Serializes all entries to a list of dictionaries."""
        return [e.to_dict() for e in self.entries]

    def summary(self) -> Dict[str, Any]:
        """Returns a high-level summary of recorded decisions across nodes."""
        node_counts: Dict[str, int] = {}
        for e in self.entries:
            node_counts[e.node] = node_counts.get(e.node, 0) + 1
        return {
            "total_decisions": len(self.entries),
            "nodes_active": list(node_counts.keys()),
            "decisions_per_node": node_counts,
            "latest_timestamp": self.entries[-1].timestamp if self.entries else None,
        }
