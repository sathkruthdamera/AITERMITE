from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class FixSuggestion:
    command: str
    explanation: str
    confidence: float
    risk: str = "medium"
    provider: str = "heuristic"
    alternatives: List[str] = field(default_factory=list)

    def confidence_label(self) -> str:
        if self.confidence >= 0.80:
            return "high"
        if self.confidence >= 0.55:
            return "medium"
        return "low"
