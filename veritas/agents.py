from crewai import Agent
from .llm import get_llm

def build_agents():
    llm = get_llm()

    content_agent = Agent(
        role="Content Analysis Specialist",
        goal="Understand the submitted digital content and extract concrete claims, requests, entities, actions and suspicious linguistic/contextual signals.",
        backstory="You specialise in interpreting messages and URLs without jumping to conclusions. Separate observations from assumptions.",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    identity_agent = Agent(
        role="Identity Verification Specialist",
        goal="Assess whether claimed identities, organisations, domains and destinations appear consistent with the available content.",
        backstory="You focus on identity consistency. Never claim independent verification when evidence was not actually provided.",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    risk_agent = Agent(
        role="Risk and Social Engineering Specialist",
        goal="Identify manipulation and risk signals including urgency, threats, secrecy, financial requests, credential requests, impersonation and unusual instructions.",
        backstory="You analyse social-engineering patterns conservatively and explain the concrete signal behind every finding.",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    evidence_agent = Agent(
        role="Evidence Correlation Specialist",
        goal="Combine the independent findings into a coherent evidence chain, highlighting corroborating signals and contradictions.",
        backstory="You are the evidence layer. Do not invent facts. Clearly distinguish observed evidence from uncertainty.",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    assessment_agent = Agent(
        role="Trust Assessment Specialist",
        goal="Produce an evidence-based trust assessment using exactly three levels: LOW RISK, NEEDS VERIFICATION, or HIGH RISK.",
        backstory="You turn correlated evidence into a clear assessment. The result is not absolute proof and uncertainty must be preserved.",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    safety_agent = Agent(
        role="Digital Safety Guidance Specialist",
        goal="Provide practical, proportionate next-step guidance based on the assessment and evidence.",
        backstory="You help ordinary users avoid unsafe actions and independently verify important claims through trusted channels.",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    return {
        "Content Analysis Agent": content_agent,
        "Identity Verification Agent": identity_agent,
        "Risk & Social Engineering Agent": risk_agent,
        "Evidence Correlation Agent": evidence_agent,
        "Trust Assessment Agent": assessment_agent,
        "Safety Guidance Agent": safety_agent,
    }
