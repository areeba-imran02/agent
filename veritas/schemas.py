from typing import List, Dict, Any
from pydantic import BaseModel, Field

class Assessment(BaseModel):
    level: str = Field(
        description="Exactly one of: LOW RISK, NEEDS VERIFICATION, HIGH RISK"
    )
    reasons: List[str] = Field(default_factory=list)

class FinalResult(BaseModel):
    assessment: Assessment
    evidence: List[str] = Field(default_factory=list)
    safer_action: str
    agent_outputs: Dict[str, Any] = Field(default_factory=dict)
