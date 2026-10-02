import json
import re
from crewai import Crew, Process
from .agents import build_agents
from .tasks import build_tasks

def _extract_level(text):
    upper = text.upper()
    if "HIGH RISK" in upper:
        return "HIGH RISK"
    if "LOW RISK" in upper:
        return "LOW RISK"
    return "NEEDS VERIFICATION"

def _reasons(text):
    # Prefer bullet-like lines after REASONS, otherwise use useful short lines.
    match = re.search(r"REASONS\s*:?(.*)", text, re.I | re.S)
    block = match.group(1) if match else text
    lines = []
    for line in block.splitlines():
        clean = re.sub(r"^[\s\-\*\d\.\)]+", "", line).strip()
        if clean and len(clean) > 8:
            lines.append(clean)
    return lines[:5] or ["The assessment is based on the available evidence."]

def _safe_text(output):
    if output is None:
        return ""
    return getattr(output, "raw", str(output))

def run_veritas(content, input_type="Text / Message"):
    agents = build_agents()
    tasks = build_tasks(agents, content, input_type)

    crew = Crew(
        agents=list(agents.values()),
        tasks=tasks,
        process=Process.sequential,
        verbose=False,
    )

    result = crew.kickoff()

    outputs = {}
    for task in tasks:
        name = task.agent.role
        outputs[name] = _safe_text(task.output)

    assessment_text = outputs.get("Trust Assessment Specialist", "")
    safety_text = outputs.get("Digital Safety Guidance Specialist", "")
    evidence_text = outputs.get("Evidence Correlation Specialist", "")

    level = _extract_level(assessment_text)

    evidence = _reasons(evidence_text)
    reasons = _reasons(assessment_text)

    return {
        "assessment": {
            "level": level,
            "reasons": reasons,
        },
        "evidence": evidence,
        "safer_action": safety_text.strip(),
        "agent_outputs": outputs,
    }
