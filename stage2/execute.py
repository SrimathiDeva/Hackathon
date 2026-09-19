"""
stage2/execute.py

Execute Node for Problem Statement 2 — MONITOR.
Executes approved queries, transmits medical escalations, and records actions.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from stage2.trace import TraceLog
from stage2.memory import ReviewMemory


class ExecuteNode:
    """
    Final execution stage.
    Dispatches approved queries and escalations to the trial gateway and monitoring hub.
    """

    def __init__(
        self,
        trace: TraceLog,
        memory: ReviewMemory,
        hub_url: str,
        gateway_url: str,
        team_key: str,
    ):
        self.trace = trace
        self.memory = memory
        self.hub_url = hub_url
        self.gateway_url = gateway_url
        self.team_key = team_key

    def process(self, gate_result: Dict[str, Any], cut: int) -> List[Dict[str, Any]]:
        """
        Executes approved monitoring actions.
        """
        executed_actions: List[Dict[str, Any]] = []

        approved_queries = gate_result.get("approved_queries", [])
        approved_escalations = gate_result.get("approved_escalations", [])
        approved_deviations = gate_result.get("approved_deviations", [])

        # 1. Execute Approved Queries
        for qry in approved_queries:
            action = {
                "action_type": "DISPATCH_QUERY",
                "target": self.gateway_url,
                "query_id": qry.query_id,
                "usubjid": qry.usubjid,
                "site_id": qry.site_id,
                "status": "DISPATCHED",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            executed_actions.append(action)

        # 2. Execute Approved Escalations
        for esc in approved_escalations:
            action = {
                "action_type": "TRANSMIT_ESCALATION",
                "target": self.hub_url,
                "escalation_id": esc.escalation_id,
                "usubjid": esc.usubjid,
                "urgency": esc.urgency,
                "status": "TRANSMITTED",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            executed_actions.append(action)

        # 3. Log Approved Deviations
        for dev in approved_deviations:
            action = {
                "action_type": "LOG_DEVIATION",
                "deviation_id": dev.deviation_id,
                "category": dev.category,
                "status": "RECORDED",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            executed_actions.append(action)

        self.trace.record(
            node="execute",
            decision="ACTIONS_EXECUTED",
            evidence=[],
            details={
                "cut": cut,
                "total_executed": len(executed_actions),
                "queries_dispatched": len(approved_queries),
                "escalations_transmitted": len(approved_escalations),
                "deviations_logged": len(approved_deviations),
            },
        )

        return executed_actions
