"""
starter/schemas.py

Standard schemas for Problem 1 (ATLAS).
Do not modify the structure of these schemas.
"""

from dataclasses import dataclass, field
from typing import Any, Optional, List, Dict, Union


@dataclass
class RecordRef:
    """
    Identifies evidence supporting an answer.
    
    Can represent:
      1. A clinical record: domain="LB", usubjid="042-S07-001", seq=25
      2. A document section: domain="DOC", document="lab-manual", section="units"
    """
    domain: str
    usubjid: Optional[str] = None
    seq: Optional[int] = None
    document: Optional[str] = None
    section: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"domain": self.domain}
        if self.usubjid is not None:
            d["usubjid"] = self.usubjid
        if self.seq is not None:
            d["seq"] = int(self.seq)
        if self.document is not None:
            d["document"] = self.document
        if self.section is not None:
            d["section"] = self.section
        return d


@dataclass
class Question:
    """
    A clinical study question.
    """
    question_id: str
    text: str
    kind: Optional[str] = None  # 'count', 'lookup', 'finding', or 'trap'


@dataclass
class Answer:
    """
    The structured answer returned by Atlas.
    """
    question_id: str
    answer: Any  # int for count, list[str] for finding/trap, or specific lookup value
    text: str
    evidence: List[Union[RecordRef, Dict[str, Any]]] = field(default_factory=list)
    confidence: float = 0.9
    steps_used: int = 1
    tokens_used: int = 0

    def to_dict(self) -> Dict[str, Any]:
        ev_list = []
        for ev in self.evidence:
            if isinstance(ev, RecordRef):
                ev_list.append(ev.to_dict())
            elif isinstance(ev, dict):
                ev_list.append(ev)
            else:
                ev_list.append(dict(ev))

        return {
            "question_id": self.question_id,
            "answer": self.answer,
            "text": self.text,
            "evidence": ev_list,
            "confidence": round(float(self.confidence), 2),
            "steps_used": int(self.steps_used),
            "tokens_used": int(self.tokens_used),
        }
