import html
import json
import os
import re
import sys

# Streamlit Cloud ships an old sqlite3; CrewAI's dependencies (chromadb) need a newer one.
try:
    __import__("pysqlite3")
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except Exception:
    pass

import streamlit as st

from veritas.config import DEFAULT_MODEL, LANGUAGES, MODEL_CHOICES, REGIONS, STEPS
from veritas.models import level_for
from veritas.perception import PerceptionError

st.set_page_config(page_title="VERITAS · Digital Trust & Safety", page_icon="🛡️", layout="wide")


def secret(name: str, default: str = "") -> str:
    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return os.environ.get(name, default)


# ------------------------------------------------------------------ style
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;700;800&family=Hanken+Grotesk:wght@400;500;700&display=swap');
html, body, .stApp, [class*="css"] { font-family: 'Hanken Grotesk', sans-serif; }
h1, h2, h3, h4, .display { font-family: 'Sora', sans-serif !important; letter-spacing: -0.02em; }
.block-container { padding-top: 1.6rem; max-width: 1200px; }
header[data-testid="stHeader"] { background: transparent; }

.brand { display:flex; align-items:baseline; gap:14px; margin-bottom: 2px; }
.brand .mark { font-family:'Sora'; font-weight:800; font-size:2.1rem; letter-spacing:.08em; }
.brand .sub { color:#8F97D6; font-size:.95rem; }
.tagline { color:#C9CEF5; font-size:1.05rem; margin-bottom: 1.4rem; }
.ask { font-family:'Sora'; font-weight:700; font-size:1.55rem; margin: .4rem 0 .8rem; }

.step { display:flex; gap:12px; align-items:flex-start; padding:10px 13px; margin-bottom:7px;
        border-radius:12px; background:#171B3A; border:1px solid #262C5E; }
.step .badge { flex:0 0 28px; height:28px; border-radius:50%; display:grid; place-items:center;
               font-family:'Sora'; font-weight:700; font-size:.8rem; background:#262C5E; color:#A9B0E3; }
.step .name { font-weight:700; font-size:.95rem; }
.step .tag { color:#A9B0E3; font-size:.8rem; }
.step .snip { color:#D5D9FF; font-size:.82rem; margin-top:5px; line-height:1.4; }
.step .state { margin-left:auto; font-size:.72rem; font-weight:700; color:#7E86C9; white-space:nowrap; padding-top:3px; }
.step.sensor .badge { border-radius:8px; }
.step.running { border-color:#7C8CFF; box-shadow:0 0 0 1px #7C8CFF inset; }
.step.running .badge { background:#7C8CFF; color:#0F1226; animation:pulse 1.3s ease-in-out infinite; }
.step.running .state { color:#9FB0FF; }
.step.done .badge { background:#39D98A; color:#0B2A1A; } .step.done .state { color:#39D98A; }
.step.error .badge { background:#FF5D6C; color:#2A0A0E; } .step.error .state { color:#FF8B96; }
@keyframes pulse { 0%,100% { transform:scale(1);} 50% { transform:scale(1.12);} }
@media (prefers-reduced-motion: reduce) { .step.running .badge { animation:none; } }

.assess-title { font-family:'Sora'; font-weight:700; letter-spacing:.14em; color:#8F97D6; font-size:.85rem; margin: 6px 0 8px; }
.verdict { display:flex; gap:26px; align-items:center; padding:24px 26px; border-radius:18px;
           background:#171B3A; border:1px solid #262C5E; margin-bottom:18px; }
.ring { --p:50; --c:#FFB547; flex:0 0 128px; height:128px; border-radius:50%; display:grid; place-items:center;
        background:conic-gradient(var(--c) calc(var(--p) * 1%), #2A3066 0); }
.ring-in { width:100px; height:100px; border-radius:50%; background:#171B3A; display:grid; place-items:center; text-align:center; }
.ring-in b { font-family:'Sora'; font-size:2rem; line-height:1; } .ring-in span { font-size:.7rem; color:#A9B0E3; display:block; }
.verdict .lvl { font-family:'Sora'; font-weight:800; font-size:1.75rem; }
.verdict .head { font-size:1.08rem; margin:4px 0 10px; }
.high { --c:#FF5D6C; } .high .lvl { color:#FF7A86; }
.mid { --c:#FFB547; } .mid .lvl { color:#FFC56B; }
.low { --c:#39D98A; } .low .lvl { color:#5BE3A0; }
.pill { display:inline-block; padding:3px 11px; border-radius:999px; background:#262C5E; color:#C9CEF5; font-size:.78rem; margin:0 6px 4px 0; }
.pill.ok { background:#12392A; color:#6CE8A8; } .pill.warn { background:#40300F; color:#FFC56B; } .pill.bad { background:#431820; color:#FF8B96; }

.why { padding:9px 13px; margin:6px 0; border-radius:10px; background:#171B3A; line-height:1.5; }
.why:before { content:'✓'; color:#7C8CFF; font-weight:800; margin-right:10px; }
.ev { padding:10px 13px; margin:7px 0; border-radius:10px; background:#171B3A; border-left:4px solid #262C5E; }
.ev.high { border-left-color:#FF5D6C; } .ev.medium { border-left-color:#FFB547; } .ev.low { border-left-color:#39D98A; }
.ev .t { font-weight:700; } .ev .d { color:#C9CEF5; font-size:.93rem; margin-top:2px; } .ev .s { color:#7E86C9; font-size:.76rem; margin-top:4px; }
.act { display:grid; grid-template-columns:1fr 1fr; gap:10px; margin:8px 0; }
.act > div { padding:11px 14px; border-radius:10px; line-height:1.45; }
.act .no { background:#33151B; border:1px solid #5A2230; } .act .yes { background:#12301F; border:1px solid #1F5A3A; }
.act small { display:block; font-weight:700; letter-spacing:.08em; margin-bottom:3px; font-size:.7rem; }
.act .no small { color:#FF8B96; } .act .yes small { color:#6CE8A8; }
@media (max-width: 700px) { .act { grid-template-columns:1fr; } .verdict { flex-direction:column; align-items:flex-start; } }
div.stButton > button[kind="primary"] { font-weight:700; border-radius:10px; min-height:2.8rem; }
.privacy { font-size:.82rem; color:#A9B0E3; line-height:1.5; }
</style>
""",
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------ state
S = st.session_state
N = len(STEPS)
S.setdefault("result", None)
S.setdefault("error", None)
S.setdefault("statuses", ["waiting"] * N)
S.setdefault("snips", [""] * N)
S.setdefault("chat", [])

EXAMPLES = {
    "Bank phishing (Roman Urdu)": "URGENT: Aap ka HBL account aaj block ho jayega. Abhi apna OTP aur PIN verify karein: "
                                  "http://hbl-secure-verify.xyz/login warna account band kar diya jayega.",
    "Prize scam (English)": "Congratulations! You have won Rs 500,000 in the BISP lucky draw. To claim your prize send a "
                            "processing fee of Rs 3,000 to JazzCash 0300-1234567 and do not tell anyone.",
    "Normal message": "Hi Sara, the meeting moved to 3pm tomorrow. I'll send the agenda this evening. Can you bring the printed report?",
}


def set_example(name: str) -> None:
    S["msg_text"] = EXAMPLES[name]


def clear_all() -> None:
    for k in ("result", "error", "chat"):
        S[k] = None if k != "chat" else []
    S.statuses, S.snips = ["waiting"] * N, [""] * N


# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.markdown("### Settings")
    key_from_secrets = secret("GROQ_API_KEY")
    if key_from_secrets:
        st.success("Groq API key loaded from Secrets", icon="🔑")
        api_key = key_from_secrets
    else:
        api_key = st.text_input("Groq API key", type="password", placeholder="gsk_...",
                                help="Free key at console.groq.com/keys. Kept only in this session.")
    default_model = secret("VERITAS_MODEL", DEFAULT_MODEL)
    choices = MODEL_CHOICES if default_model in MODEL_CHOICES else [default_model] + MODEL_CHOICES
    model = st.selectbox("Groq model (agents)", choices, index=choices.index(default_model),
                         help="If Groq retires a model, pick another one here.")
    region = st.selectbox("Region pack", list(REGIONS), index=list(REGIONS).index("Pakistan"),
                          help="Global core + modular localization. Pakistan adds local scam patterns and payment context.")
    language = st.selectbox("Explanation language", list(LANGUAGES))
    st.divider()
    st.markdown("**Try an example**")
    for name in EXAMPLES:
        st.button(name, on_click=set_example, args=(name,), use_container_width=True, key=f"ex_{name}")
    st.divider()
    st.markdown("**Privacy**")
    st.markdown(
        '<div class="privacy">You choose what to upload. VERITAS saves nothing: files and text stay in memory for this '
        "session only. To analyse them, the content is sent to Groq's API. Use the button below to wipe this session.</div>",
        unsafe_allow_html=True,
    )
    st.button("Clear this session", on_click=clear_all, use_container_width=True)


# ------------------------------------------------------------------ helpers
def esc(x) -> str:
    return html.escape(str(x))


def snippet(text: str, n: int = 120) -> str:
    for line in str(text).splitlines():
        line = re.sub(r"[#*`>_\-|]+", " ", line).strip()
        if len(line) > 12:
            return line[: n - 1] + "…" if len(line) > n else line
    return ""


STATE_LABEL = {"waiting": "Waiting", "running": "Working…", "done": "Done", "error": "Failed"}


def team_html() -> str:
    rows = []
    for i, s in enumerate(STEPS):
        stt = S.statuses[i]
        sn = f'<div class="snip">{esc(S.snips[i])}</div>' if S.snips[i] else ""
        cls = f"step {stt}" + (" sensor" if s["kind"] == "sensor" else "")
        rows.append(
            f'<div class="{cls}"><div class="badge">{i + 1}</div><div><div class="name">{esc(s["role"])}</div>'
            f'<div class="tag">{esc(s["tagline"])}</div>{sn}</div><div class="state">{STATE_LABEL[stt]}</div></div>'
        )
    return "".join(rows)


def friendly_error(e: Exception) -> str:
    m, low = str(e), str(e).lower()
    if "401" in low or "invalid api key" in low or "authentication" in low:
        return "Groq rejected the API key. Check the key in the sidebar (it starts with gsk_)."
    if "429" in low or "rate limit" in low or "rate_limit" in low:
        return "Groq rate limit reached. Wait about a minute and try again, or pick the smaller model in the sidebar."
    if "decommission" in low or "model_not_found" in low or "does not exist" in low or "no longer supported" in low:
        return "This Groq model is not available any more. Pick a different model in the sidebar."
    return f"The team could not finish: {m[:400]}"


# ------------------------------------------------------------------ header
st.markdown(
    '<div class="brand"><span class="mark">VERITAS</span><span class="sub">Digital Trust &amp; Safety Platform</span></div>'
    '<div class="tagline">Understand. Verify. Trust.</div>',
    unsafe_allow_html=True,
)
st.markdown('<div class="ask">What would you like to verify?</div>', unsafe_allow_html=True)

left, right = st.columns([1.3, 1], gap="large")
with right:
    st.markdown("#### The VERITAS team")
    team_box = st.empty()
    team_box.markdown(team_html(), unsafe_allow_html=True)


def analyze(kind: str, **kw) -> None:
    from veritas.orchestrator import run_case  # imported lazily so the page loads fast

    if not api_key:
        S.error = "Add your Groq API key in the sidebar first (free at console.groq.com/keys)."
        return
    S.error, S.result, S.chat = None, None, []
    S.statuses = ["running"] + ["waiting"] * (N - 1)
    S.snips = [""] * N
    team_box.markdown(team_html(), unsafe_allow_html=True)

    def on_event(i: int, role: str, text: str) -> None:
        S.statuses[i] = "done"
        S.snips[i] = snippet(text)
        if i + 1 < N:
            S.statuses[i + 1] = "running"
        team_box.markdown(team_html(), unsafe_allow_html=True)

    try:
        with st.spinner("The team is working on your case…"):
            S.result = run_case(kind=kind, region=region, language=language, model=model, api_key=api_key,
                                on_event=on_event, **kw)
        S.statuses = ["done"] * N
    except PerceptionError as e:
        S.statuses = ["error" if s == "running" else s for s in S.statuses]
        S.error = str(e)
    except Exception as e:  # noqa: BLE001
        S.statuses = ["error" if s == "running" else s for s in S.statuses]
        S.error = friendly_error(e)
    team_box.markdown(team_html(), unsafe_allow_html=True)


with left:
    t_text, t_img, t_url, t_qr, t_aud = st.tabs(["Paste text", "Upload image", "Check URL", "Scan QR", "Upload audio"])

    with t_text:
        text = st.text_area("Text", key="msg_text", height=190, label_visibility="collapsed",
                            placeholder="Paste the message, email or conversation here (English, Urdu or Roman Urdu)…")
        note = st.text_input("Anything we should know? (optional)", key="msg_note",
                             placeholder="e.g. I don't have an account with this bank")
        if st.button("Analyse", type="primary", use_container_width=True, key="go_text"):
            if text.strip():
                analyze("text", text=text, note=note)
            else:
                st.warning("Paste some text first.")

    with t_img:
        img = st.file_uploader("Screenshot or image", type=["png", "jpg", "jpeg", "webp"], label_visibility="collapsed", key="f_img")
        inote = st.text_input("What were you told about it? (optional)", key="img_note",
                              placeholder="e.g. a stranger sent this as proof of payment")
        if img:
            st.image(img, width=300)
        if st.button("Analyse", type="primary", use_container_width=True, key="go_img"):
            if img:
                analyze("image", image=img.getvalue(), note=inote)
            else:
                st.warning("Upload an image first.")

    with t_url:
        link = st.text_input("URL", key="url_in", label_visibility="collapsed", placeholder="https://example.com/verify")
        uctx = st.text_area("Message that came with this link (optional)", key="url_ctx", height=100)
        if st.button("Analyse", type="primary", use_container_width=True, key="go_url"):
            if link.strip():
                analyze("url", url=link, text=uctx)
            else:
                st.warning("Enter a URL first.")

    with t_qr:
        qr = st.file_uploader("QR code image", type=["png", "jpg", "jpeg", "webp"], label_visibility="collapsed", key="f_qr")
        qnote = st.text_input("Where did you find this QR code? (optional)", key="qr_note",
                              placeholder="e.g. sticker on a parking meter, or in an email from my 'bank'")
        if qr:
            st.image(qr, width=220)
        if st.button("Analyse", type="primary", use_container_width=True, key="go_qr"):
            if qr:
                analyze("qr", image=qr.getvalue(), note=qnote)
            else:
                st.warning("Upload a QR image first.")

    with t_aud:
        aud = st.file_uploader("Voice note or call recording", type=["wav", "mp3", "m4a", "ogg", "webm", "flac"],
                               label_visibility="collapsed", key="f_aud")
        anote = st.text_input("What did the voice ask you to do? (optional)", key="aud_note")
        if aud:
            st.audio(aud)
        if st.button("Analyse", type="primary", use_container_width=True, key="go_aud"):
            if aud:
                analyze("audio", audio=aud.getvalue(), audio_name=aud.name, note=anote)
            else:
                st.warning("Upload an audio file first.")

    if S.error:
        st.error(S.error)


# ------------------------------------------------------------------ result dashboard
IDENTITY_PILL = {"Consistent": "ok", "Needs Verification": "warn", "Mismatch Detected": "bad", "No Claim Made": ""}


def render_result(res: dict) -> None:
    a = res["assessment"]
    level = level_for(a["score"])
    cls = {"HIGH RISK": "high", "NEEDS VERIFICATION": "mid", "LOW RISK": "low"}[level]
    icon = {"HIGH RISK": "🔴", "NEEDS VERIFICATION": "🟡", "LOW RISK": "🟢"}[level]
    st.markdown('<div class="assess-title">VERITAS ASSESSMENT</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="verdict {cls}"><div class="ring" style="--p:{a["score"]}"><div class="ring-in"><div><b>{a["score"]}</b>'
        f"<span>risk / 100</span></div></div></div><div>"
        f'<div class="lvl">{icon} {esc(level.title())}</div><div class="head">{esc(a["headline"])}</div>'
        f'<span class="pill {IDENTITY_PILL.get(a["identity_consistency"], "")}">Identity: {esc(a["identity_consistency"])}</span>'
        f'<span class="pill">{esc(a["scam_type"])}</span><span class="pill">confidence: {esc(a["confidence"])}</span>'
        f"</div></div>",
        unsafe_allow_html=True,
    )

    st.markdown("#### Why?")
    for w in a["why"] or ["No clear reasons were returned."]:
        st.markdown(f'<div class="why">{esc(w)}</div>', unsafe_allow_html=True)

    with st.expander("Evidence · view details"):
        for e in sorted(a["evidence"], key=lambda x: {"high": 0, "medium": 1, "low": 2}[x["severity"]]):
            src = f'<div class="s">{esc(e["source"])} · {esc(e["severity"])}</div>' if e["source"] else ""
            st.markdown(f'<div class="ev {e["severity"]}"><div class="t">{esc(e["title"])}</div>'
                        f'<div class="d">{esc(e["detail"])}</div>{src}</div>', unsafe_allow_html=True)
        if not a["evidence"]:
            st.caption("No evidence items were returned.")

    st.markdown("#### Recommended action")
    for x in a["actions"] or [{"dont": "Don't act on this yet.", "instead": "Verify through an official channel first."}]:
        st.markdown(f'<div class="act"><div class="no"><small>DON\'T</small>{esc(x["dont"])}</div>'
                    f'<div class="yes"><small>INSTEAD</small>{esc(x["instead"])}</div></div>', unsafe_allow_html=True)

    with st.expander("How to verify safely"):
        for i, s in enumerate(a["verify_steps"] or ["Contact the organisation through its official website, app or a number you already trust."], 1):
            st.markdown(f"**{i}.** {s}")

    with st.expander("What each agent reported"):
        reports = res["reports"]
        if reports:
            tabs = st.tabs([r["role"] for r in reports])
            for t, r in zip(tabs, reports):
                with t:
                    st.markdown(r["text"])
    with st.expander("What VERITAS read from your input"):
        st.markdown(f"**Input type:** {res['kind']}  ·  **Region:** {res['region']}")
        st.text(res["perceived"][:3000])
        if res["urls"]:
            st.markdown("**Links found:** " + ", ".join(f"`{u}`" for u in res["urls"]))

    # ---- follow-up questions
    st.markdown("#### Ask VERITAS about this result")
    q_cols = st.columns(3)
    quick = ["Why is this suspicious?", "Explain this in Urdu", "What if I already clicked or paid?"]
    asked = None
    for c, q in zip(q_cols, quick):
        if c.button(q, use_container_width=True, key=f"q_{q}"):
            asked = q
    typed = st.text_input("Your question", key="followup_in", label_visibility="collapsed", placeholder="Ask anything about this case…")
    if st.button("Ask", key="ask_btn") and typed.strip():
        asked = typed.strip()
    if asked:
        from veritas.chat import ask_followup
        try:
            with st.spinner("Thinking…"):
                answer = ask_followup(asked, res, S.chat, model, api_key)
            S.chat += [{"role": "user", "content": asked}, {"role": "assistant", "content": answer}]
        except Exception as e:  # noqa: BLE001
            st.error(friendly_error(e))
    for m in S.chat:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    st.download_button("Download report (JSON)", json.dumps(res, indent=2, ensure_ascii=False),
                       file_name="veritas_report.json", mime="application/json")
    st.caption("VERITAS gives an evidence-based assessment, not absolute proof. When money or logins are involved, "
               "confirm through the official app or a number you already trust.")


if S.result:
    st.divider()
    render_result(S.result)
