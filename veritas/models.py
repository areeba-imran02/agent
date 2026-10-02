"""Structured assessment + tolerant parsing. No CrewAI import, so it is unit-testable."""
from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    title: str = Field(description="Short name of the evidence")
    detail: str = Field(description="One or two plain sentences explaining it")
    severity: str = Field(default="medium", description="low, medium or high")
    source: str = Field(default="", description="Which agent found it")


class ActionItem(BaseModel):
    dont: str = Field(description="What the user should NOT do")
    instead: str = Field(description="What the user should do instead")


class TrustAssessment(BaseModel):
    score: int = Field(description="Risk 0 (no warning signals) to 100 (almost certainly fraud)")
    identity_consistency: str = Field(description="Exactly one of: Consistent, Needs Verification, Mismatch Detected, No Claim Made")
    scam_type: str = Field(description="Short category, e.g. 'Bank phishing' or 'None detected'")
    headline: str = Field(description="One-sentence assessment for the user")
    why: list[str] = Field(default_factory=list, description="3-5 short reasons, each one a plain sentence")
    evidence: list[EvidenceItem] = Field(default_factory=list, description="Evidence ledger, max 8 items")
    actions: list[ActionItem] = Field(default_factory=list, description="2-3 Don't / Instead pairs")
    verify_steps: list[str] = Field(default_factory=list, description="3-5 steps to verify safely")
    confidence: str = Field(default="medium", description="low, medium or high")


def level_for(score: int) -> str:
    return "HIGH RISK" if score >= 65 else "NEEDS VERIFICATION" if score >= 35 else "LOW RISK"


def _identity(v: Any) -> str:
    s = str(v or "").lower()
    if "mismatch" in s or "inconsist" in s:
        return "Mismatch Detected"
    if "no claim" in s or "not claim" in s or "none" in s:
        return "No Claim Made"
    if "consistent" in s:
        return "Consistent"
    return "Needs Verification"


def _strs(x: Any, n: int) -> list[str]:
    if isinstance(x, list):
        return [str(i) for i in x if str(i).strip()][:n]
    return [str(x)] if x else []


def _clean(v: dict[str, Any]) -> dict[str, Any]:
    try:
        score = max(0, min(100, int(round(float(v.get("score", 50))))))
    except (TypeError, ValueError):
        score = 50
    ev = []
    for e in (v.get("evidence") or [])[:8]:
        if isinstance(e, dict):
            sev = str(e.get("severity", "medium")).lower()
            ev.append({"title": str(e.get("title", "Evidence")), "detail": str(e.get("detail", "")),
                       "severity": sev if sev in ("low", "medium", "high") else "medium",
                       "source": str(e.get("source", ""))})
        else:
            ev.append({"title": str(e), "detail": "", "severity": "medium", "source": ""})
    acts = []
    for a in (v.get("actions") or [])[:4]:
        if isinstance(a, dict):
            acts.append({"dont": str(a.get("dont", "")), "instead": str(a.get("instead", ""))})
        else:
            acts.append({"dont": "", "instead": str(a)})
    return {
        "score": score, "level": level_for(score),
        "identity_consistency": _identity(v.get("identity_consistency")),
        "scam_type": str(v.get("scam_type") or "Unclear"),
        "headline": str(v.get("headline") or ""),
        "why": _strs(v.get("why"), 6), "evidence": ev, "actions": acts,
        "verify_steps": _strs(v.get("verify_steps"), 6),
        "confidence": str(v.get("confidence") or "medium").lower(),
    }


def parse_assessment(pydantic_obj: Any, raw: str | None) -> dict[str, Any]:
    """Prefer CrewAI's parsed pydantic; fall back to JSON inside the raw text; last resort: a cautious default."""
    if pydantic_obj is not None:
        try:
            return _clean(pydantic_obj.model_dump())
        except Exception:
            pass
    raw = raw or ""
    m = re.search(r"\{.*\}", raw, re.S)
    if m:
        try:
            return _clean(json.loads(m.group(0)))
        except Exception:
            pass
    return _clean({"score": 50, "identity_consistency": "Needs Verification", "scam_type": "Unclear",
                   "headline": "The assessor did not return a structured result, so treat this as unverified.",
                   "why": [raw[:300]] if raw else [], "confidence": "low",
                   "actions": [{"dont": "Do not act on this content yet.",
                                "instead": "Verify through an official website, app or number you already trust."}]})
