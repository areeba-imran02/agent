from crewai import Task

def build_tasks(agents, content, input_type):
    content_task = Task(
        description=f"""
Analyse this {input_type} submitted by the user:

--- INPUT ---
{content}
--- END INPUT ---

Extract:
1. What the content claims.
2. What action it asks the user to take.
3. Mentioned organisations, people, domains or destinations.
4. Any observable suspicious language or contextual signals.
5. What cannot be established from the input alone.

Do not invent external facts.
""",
        expected_output="A concise structured analysis containing observations, claims, requested actions and uncertainties.",
        agent=agents["Content Analysis Agent"],
    )

    identity_task = Task(
        description=f"""
Assess identity consistency for this {input_type}:

{content}

Use the content analysis supplied by the previous agent when available.
Look for consistency or mismatch between claimed organisation/sender, domain/destination,
message context and visible identity cues.

Important: do not claim that an organisation or domain was independently verified unless
such evidence is actually available.
""",
        expected_output="Identity consistency findings with evidence and uncertainty.",
        agent=agents["Identity Verification Agent"],
        context=[content_task],
    )

    risk_task = Task(
        description=f"""
Analyse the following input for fraud and social-engineering risk signals:

{content}

Look specifically for urgency, threats, pressure, secrecy, financial requests,
credential requests, impersonation, suspicious instructions, sensitive actions,
and attempts to bypass normal verification.

Only report signals supported by the content.
""",
        expected_output="A list of concrete risk signals and their supporting observations.",
        agent=agents["Risk & Social Engineering Agent"],
        context=[content_task],
    )

    evidence_task = Task(
        description="""
Correlate the outputs from content, identity and risk analysis.

Create an evidence chain:
- corroborating signals
- contradictions or missing evidence
- important uncertainties
- the strongest reasons supporting caution

Do not manufacture facts.
""",
        expected_output="A concise evidence correlation report.",
        agent=agents["Evidence Correlation Agent"],
        context=[content_task, identity_task, risk_task],
    )

    assessment_task = Task(
        description="""
Using the evidence correlation, select exactly ONE assessment:

LOW RISK
NEEDS VERIFICATION
HIGH RISK

Use HIGH RISK only when multiple significant warning signals are supported.
Use NEEDS VERIFICATION when evidence is incomplete, unusual or uncertain.
Use LOW RISK only when no major warning signals are apparent from the supplied evidence.

Return:
LEVEL: ...
REASONS:
- ...
- ...
""",
        expected_output="Exactly one assessment level plus 2-5 concise evidence-based reasons.",
        agent=agents["Trust Assessment Agent"],
        context=[evidence_task],
    )

    safety_task = Task(
        description="""
Provide the safest practical next action based on the assessment and evidence.

Give:
1. One clear action the user should take.
2. One important action to avoid, when relevant.
3. An independent verification method where appropriate.

Do not use alarmist language and do not claim certainty beyond the evidence.
""",
        expected_output="A concise, user-friendly safer-action recommendation.",
        agent=agents["Safety Guidance Agent"],
        context=[assessment_task, evidence_task],
    )

    return [
        content_task,
        identity_task,
        risk_task,
        evidence_task,
        assessment_task,
        safety_task,
    ]
