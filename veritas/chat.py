"""Follow-up questions about a finished assessment ('Why is this suspicious?', 'Explain this in Urdu')."""
from __future__ import annotations

from .crew import make_llm


def ask_followup(question: str, result: dict, history: list[dict], model: str, api_key: str) -> str:
    a = result["assessment"]
    ev = "\n".join(f"- [{e['severity']}] {e['title']}: {e['detail']}" for e in a["evidence"])
    context = (
        f"Case content:\n{result['content'][:1500]}\n\nLinks: {', '.join(result['urls']) or 'none'}\n"
        f"Assessment: {a['level']} (score {a['score']}/100), identity: {a['identity_consistency']}, type: {a['scam_type']}\n"
        f"Headline: {a['headline']}\nEvidence:\n{ev}\n"
    )
    system = ("You are VERITAS, a calm digital-safety assistant. Answer ONLY from the case below; if something is not in "
              "the evidence, say you cannot tell. Be short, practical and kind. If asked to explain in Urdu or Roman Urdu, do so. "
              "Never claim absolute certainty; this is an evidence-based assessment, not proof.\n\n" + context)
    messages = [{"role": "system", "content": system}] + history[-6:] + [{"role": "user", "content": question}]
    return str(make_llm(model, api_key).call(messages)).strip()
