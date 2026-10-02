# VERITAS — Digital Trust & Safety Platform

**Understand. Verify. Trust.**

VERITAS is a CrewAI-based multi-agent prototype that helps users assess suspicious digital content before they click, pay, respond or trust.

## Architecture

1. Content Analysis Agent
2. Identity Verification Agent
3. Risk & Social Engineering Agent
4. Evidence Correlation Agent
5. Trust Assessment Agent
6. Safety Guidance Agent

Flow:

`User Input → Content + Identity + Risk → Evidence → Trust Assessment → Safer Action`

## Current working scope

The included prototype supports:

- Text / suspicious messages
- URLs
- Coordinated six-agent reasoning
- Groq LLM
- Streamlit dashboard
- Evidence-based explanation
- Safer-action guidance

The architecture is intentionally modular so image, screenshot, QR and audio tools can be added later.

## Setup

### 1. Create environment

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install

```bash
pip install -r requirements.txt
```

### 3. Configure Groq

Copy `.env.example` to `.env` and add your key:

```text
GROQ_API_KEY=your_key
GROQ_MODEL=openai/gpt-oss-20b
```

Do not commit `.env` to GitHub.

### 4. Run

```bash
streamlit run app.py
```

## Example test

Paste:

> URGENT! Your account will be suspended today. Verify immediately using this link: https://example.com/login

The agents should identify signals such as urgency, account-related pressure and suspicious destination/context, then produce an evidence-based assessment and safer action.

## Important

VERITAS provides an evidence-based assessment, not absolute proof. Users should independently verify important claims through trusted channels.

## Project structure

```text
VERITAS/
├── app.py
├── requirements.txt
├── .env.example
├── README.md
└── veritas/
    ├── __init__.py
    ├── agents.py
    ├── tasks.py
    ├── crew.py
    ├── llm.py
    └── schemas.py
```
