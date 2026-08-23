"""Evidence domain models and relations for TRACE v0.2."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
import uuid
from pydantic import BaseModel, Field


class EvidenceType(str, Enum):
    """Classification of evidence strength and origin."""
    DIRECT = "DIRECT"    # Directly observed from deterministic tool execution (stdout, stderr, AST, exit code)
    DERIVED = "DERIVED"  # Logical inference or causal synthesis from direct observations (never presented as direct fact)


class EvidenceRelation(str, Enum):
    """Relationship between an evidence item and a hypothesis."""
    SUPPORTS = "SUPPORTS"          # Observation evidence aligns with hypothesis predictions
    CONTRADICTS = "CONTRADICTS"    # Observation evidence refutes hypothesis predictions
    DERIVED_FROM = "DERIVED_FROM"  # Inferred evidence item links back to an underlying direct observation
    VERIFIES = "VERIFIES"          # Targeted countercheck experiment conclusively verified hypothesis
    DISPROVES = "DISPROVES"        # Targeted countercheck experiment directly disproved hypothesis


class Evidence(BaseModel):
    """
    An atomic unit of evidence extracted from a tool observation.
    Answers: What was observed? Which tool? Which observation? Which hypothesis? How reliable?
    """
    id: str = Field(default_factory=lambda: f"evi_{uuid.uuid4().hex[:8]}")
    observation_id: str
    tool_name: str
    evidence_type: EvidenceType = EvidenceType.DIRECT
    statement: str
    raw_fact: Dict[str, Any] = Field(default_factory=dict)
    target_hypothesis_id: str
    relation: EvidenceRelation = EvidenceRelation.SUPPORTS
    confidence_weight: float = Field(default=1.0, ge=0.0, le=1.0)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def is_direct(self) -> bool:
        """Returns True if this evidence represents a direct tool observation fact."""
        return self.evidence_type == EvidenceType.DIRECT

    def is_supporting(self) -> bool:
        """Returns True if this evidence supports or verifies the target hypothesis."""
        return self.relation in (EvidenceRelation.SUPPORTS, EvidenceRelation.VERIFIES)

    def is_contradicting(self) -> bool:
        """Returns True if this evidence contradicts or disproves the target hypothesis."""
        return self.relation in (EvidenceRelation.CONTRADICTS, EvidenceRelation.DISPROVES)
