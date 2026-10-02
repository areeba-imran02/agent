"""Builds and runs the CrewAI team: 7 agents, sequential process, Groq through LiteLLM."""
from __future__ import annotations

import os
from typing import Callable

from . import heuristics as h
from .config import AGENTS, DEFAULT_MODEL, LANGUAGES, REGIONS
from .models import TrustAssessment, parse_assessment

# Quiet CrewAI telemetry (important on hosted apps).
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("CREWAI_DISABLE_TRACKING", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

EventCb = Callable[[int, str, str], None]  # (agent_index, role, text)
CONCISE = "Be concise: maximum 120 words, short bullet points."


def make_llm(model: str, api_key: str):
    """Groq via CrewAI's LiteLLM route: the model id must start with 'groq/'."""
    from crewai import LLM

    model = (model or DEFAULT_MODEL).strip()
    if not model.startswith("groq/"):
        model = f"groq/{model}"
    os.environ["GROQ_API_KEY"] = api_key
    return LLM(model=model, api_key=api_key, temperature=0.2, max_tokens=4096)


def url_precheck(urls: list[str]) -> str:
    if not urls:
        return "No links or QR destinations were found."
    lines = []
    for u in urls[:5]:
        r = h.analyze_url_signals(u)
        flags = "; ".join(f["title"] for f in r["findings"] if f.get("weight", 0) > 0) or "no structural red flags"
        lines.append(f"- {u} -> automated risk {r['risk']}/100 ({flags})")
    return "\n".join(lines)


def build_crew(model: str, api_key: str, on_task_done=None):
    from crewai import Agent, Crew, Process, Task

    from .crew_tools import inspect_url, official_domains

    llm = make_llm(model, api_key)
    spec = {a["key"]: a for a in AGENTS}
    tools = {"identity": [official_domains], "destination": [inspect_url]}

    def agent(key: str) -> Agent:
        a = spec[key]
        return Agent(role=a["role"], goal=a["goal"], backstory=a["backstory"], llm=llm,
                     tools=tools.get(key, []), allow_delegation=False, verbose=False, max_iter=6)

    A = {k: agent(k) for k in spec}
    CASE = ("Input type: {input_type}\nUser's note: {note}\nRegion: {region}\n"
            "--- BEGIN CONTENT ---\n{content}\n--- END CONTENT ---\n"
            "Links found: {urls}\n")

    t_content = Task(
        description=CASE + "\nUNDERSTAND this content. Give: (1) what it is and the context, (2) language, "
                    "(3) who the sender claims to be, (4) what the user is asked to do, (5) every link, phone number, "
                    "amount and deadline. Quote exact words. Do not judge risk. " + CONCISE,
        expected_output="A short case file with the five items, with exact quotes.",
        agent=A["content"])

    t_identity = Task(
        description="VERIFY the claimed identity. For every organisation or person named in the case file, call the "
                    "official_domains tool, then compare with the links, channel and wording actually used. Consider whether "
                    "that organisation ever contacts people this way or asks for OTP, PIN or passwords.\n"
                    "First line must be exactly: 'Identity consistency: X' where X is one of Consistent, Needs Verification, "
                    "Mismatch Detected, No Claim Made. Then give the evidence for and against. " + CONCISE,
        expected_output="'Identity consistency: X' then short evidence.",
        agent=A["identity"], context=[t_content])

    t_dest = Task(
        description="VERIFY the destinations. Automated pre-check:\n{url_precheck}\n\nCall the inspect_url tool for EACH link "
                    "(max 5) and combine with the pre-check. Explain in plain words why each is suspicious or ordinary. "
                    "Say that you cannot open the page, so structure is evidence, not proof. If there are no links, say so. "
                    "End with 'Destination risk: N/100'. " + CONCISE,
        expected_output="Per-link findings, then 'Destination risk: N/100'.",
        agent=A["destination"], context=[t_content])

    t_fraud = Task(
        description="ANALYSE fraud and manipulation signals in the content below. Look for urgency, fear, authority, greed, "
                    "secrecy, financial requests, and requests for sensitive data (OTP, PIN, password, CNIC, card). "
                    "For each signal: name it, quote the exact phrase, rate it low/medium/high. Say clearly if the tone is "
                    "normal and harmless.\nContent:\n{content}\nEnd with 'Manipulation risk: N/100'. " + CONCISE,
        expected_output="Signals with quotes and strength, then 'Manipulation risk: N/100'.",
        agent=A["fraud"], context=[t_content])

    t_regional = Task(
        description="Apply the regional context for region '{region}'.\n{region_pack}\n\nDoes the content match a known local "
                    "scam pattern, payment ecosystem or institutional behaviour? Only use facts from the pack. "
                    "If region is Global, say general patterns only. End with 'Regional match: none / possible / strong'. " + CONCISE,
        expected_output="Local pattern match with reasoning, then 'Regional match: ...'.",
        agent=A["regional"], context=[t_content])

    t_evidence = Task(
        description="CORRELATE. Read the reports of the Content, Identity, Destination, Fraud and Regional agents. Build ONE "
                    "evidence ledger: each item = title, detail, severity (low/medium/high), source agent. Then list "
                    "combinations that are stronger together (e.g. identity mismatch + urgency + payment request), "
                    "contradictions between agents, and what evidence is MISSING (e.g. a screenshot alone cannot prove the "
                    "recipient is legitimate). Do not copy the reports. Max 180 words.",
        expected_output="Evidence ledger, strong combinations, and missing evidence.",
        agent=A["evidence"], context=[t_content, t_identity, t_dest, t_fraud, t_regional])

    t_assess = Task(
        description="ASSESS, EXPLAIN and GUIDE. Using the evidence ledger and the specialist reports, produce the final "
                    "trust assessment.\nRules: score 0-100 where >=65 is high risk, 35-64 needs verification, <35 low risk. "
                    "One strong signal (e.g. look-alike bank domain + OTP request) outweighs several weak ones. Do NOT call "
                    "everything a scam: if the evidence is incomplete (e.g. only a payment screenshot), choose Needs "
                    "Verification and say what is missing. Never claim absolute proof.\n"
                    "'identity_consistency' must be exactly one of: Consistent, Needs Verification, Mismatch Detected, No Claim Made.\n"
                    "'why' = 3-5 short reasons. 'actions' = 2-3 pairs: dont (what NOT to do) and instead (what to do). "
                    "'verify_steps' = 3-5 concrete steps using official channels.\n"
                    "LANGUAGE: {language_rule} (Keep the 'identity_consistency' and 'severity' values in English.)",
        expected_output="The structured trust assessment.",
        agent=A["assessor"], context=[t_evidence, t_content, t_identity, t_dest],
        output_pydantic=TrustAssessment)

    return Crew(agents=[A[k] for k in spec], tasks=[t_content, t_identity, t_dest, t_fraud, t_regional, t_evidence, t_assess],
                process=Process.sequential, task_callback=on_task_done, verbose=False)


def run_crew(*, input_type: str, content: str, urls: list[str], note: str, region: str, language: str,
             model: str, api_key: str, on_event: EventCb | None = None) -> dict:
    done = {"n": 0}
    roles = [a["role"] for a in AGENTS]

    def on_task_done(out) -> None:
        i = done["n"]
        done["n"] += 1
        if on_event:
            try:
                on_event(i, roles[i] if i < len(roles) else "Agent", str(getattr(out, "raw", out)))
            except Exception:
                pass  # a UI hiccup must never break the crew

    crew = build_crew(model, api_key, on_task_done)
    result = crew.kickoff(inputs={
        "input_type": input_type, "content": content or "(no text, see links)", "note": note or "none",
        "region": region, "region_pack": REGIONS.get(region, REGIONS["Global"]),
        "urls": ", ".join(urls) if urls else "none", "url_precheck": url_precheck(urls),
        "language_rule": LANGUAGES.get(language, LANGUAGES["Auto (same as input)"]),
    })
    reports = [{"role": roles[i] if i < len(roles) else "Agent", "text": str(getattr(t, "raw", t))}
               for i, t in enumerate(getattr(result, "tasks_output", []) or [])]
    assessment = parse_assessment(getattr(result, "pydantic", None), getattr(result, "raw", ""))
    return {"assessment": assessment, "reports": reports}
