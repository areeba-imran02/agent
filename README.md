# VERITAS - Digital Trust & Safety Platform
*Understand. Verify. Trust.*

CrewAI multi-agent team + Groq LLM + Streamlit UI. Concept document ke flow ke mutabiq:
`Input -> Understand -> Verify -> Analyse -> Correlate -> Assess -> Explain -> Guide`

## Team: 7 agents + 1 perception sensor

| Stage | Agent | Kaam | Tool |
|---|---|---|---|
| Sense | **Input Perception** (sensor, LLM agent nahi) | Screenshot ko Groq vision (`qwen/qwen3.8-27b`) se, voice note ko Groq Whisper (`whisper-large-v3-turbo`) se, QR ko OpenCV se parhta hai | - |
| Understand | **Content Agent** | Content ka matlab, context, sender claim, links, amounts | - |
| Verify | **Identity Agent** | Claimed identity vs evidence: Consistent / Needs Verification / Mismatch Detected / No Claim Made | `official_domains` |
| Verify | **Destination Agent** | Har URL / QR destination ka structure check | `inspect_url` |
| Analyse | **Fraud & Manipulation Agent** | Urgency, payment request, OTP/PIN maangna, social engineering | - |
| Analyse | **Regional Context Agent** | Region pack (Pakistan / Global) se local scam patterns | - |
| Correlate | **Evidence Engine** | Sab reports ko ek evidence ledger mein jodta hai, missing evidence batata hai | - |
| Assess + Explain + Guide | **Trust Assessor** | Final score, Why, Evidence, Don't / Instead actions, Verify steps (Pydantic output) | - |

**Trust Orchestrator** = `veritas/orchestrator.py` + CrewAI `Crew(process=sequential)`.
Perception pehle chalta hai, phir 7 agents ek ke baad ek, har agent pichlay agents ki report `context` mein dekhta hai.

## UI (concept document ke hisaab se)
- "What would you like to verify?" -> Paste text / Upload image / Check URL / Scan QR / Upload audio
- Live team panel: har agent Waiting -> Working -> Done
- VERITAS ASSESSMENT: Low / Needs Verification / High + risk ring + Identity pill
- Why? / Evidence (view details) / Recommended action (Don't vs Instead) / How to verify safely
- Ask VERITAS: "Why is this suspicious?", "Explain this in Urdu", ya apna sawal
- Sidebar: region pack, explanation language (Auto / English / Urdu / Roman Urdu), privacy, Clear session

## Run locally
```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # GROQ_API_KEY daalo
streamlit run app.py
```
Key sidebar mein paste karna bhi chalta hai.

## Streamlit Cloud deploy
1. Is folder ka content GitHub repo ke **root** mein rakho (`app.py` root mein).
2. share.streamlit.io -> New app -> Main file `app.py`.
3. Advanced settings: Python **3.11**. Secrets mein: `GROQ_API_KEY = "gsk_..."`
4. Pehli build 3-5 minute le sakti hai (crewai bhaari hai).

## Groq notes
- Agents ka default model `openai/gpt-oss-120b` (CrewAI mein `groq/openai/gpt-oss-120b`).
  `llama-3.3-70b-versatile` ab Groq par sirf Enterprise ke liye hai.
- Free tier par rate limit (429) aa sakti hai kyunke ek case mein 7 LLM calls hoti hain. Aisa ho to 1 minute ruko
  ya sidebar se `openai/gpt-oss-20b` chuno. Agents ke jawab jaan booojh kar chhote (max 120 words) rakhe hain.
- Models retire hote rehte hain: https://console.groq.com/docs/deprecations

## Demo se pehle verify karo
`veritas/config.py` ke Pakistan pack mein 2 numbers hain (BISP SMS `8171`, FIA Cyber Crime helpline `1991`).
Mujhe yaad se likhe hain, live source se verify nahi kiye. Demo se pehle official sites par confirm kar lo.

## Files
```
app.py                    Streamlit UI
veritas/config.py         7 agents ki definitions, models, languages, region packs
veritas/crew.py           CrewAI Agents / Tasks / Crew
veritas/crew_tools.py     @tool inspect_url, official_domains
veritas/perception.py     image (Groq vision), audio (Groq Whisper), QR (OpenCV)
veritas/orchestrator.py   Trust Orchestrator: perception -> crew
veritas/chat.py           follow-up sawal
veritas/models.py         TrustAssessment (pydantic) + tolerant parser
veritas/heuristics.py     offline URL / brand / QR checks (tools ke andar)
tests/test_core.py        offline tests
```
