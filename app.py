import streamlit as st
from veritas.crew import run_veritas

st.set_page_config(
    page_title="VERITAS — Digital Trust & Safety",
    page_icon="🛡️",
    layout="wide",
)

st.markdown("""
<style>
.stApp { background: #f7f8fb; }
.block-container { max-width: 1200px; padding-top: 2rem; }
.hero {
    padding: 28px 30px; border-radius: 18px;
    background: linear-gradient(135deg,#171a2b,#2d3152);
    color: white; margin-bottom: 22px;
}
.hero h1 { margin: 0; font-size: 42px; }
.hero p { margin: 7px 0 0; font-size: 17px; opacity: .9; }
.card {
    background: white; border: 1px solid #e6e8ef;
    border-radius: 16px; padding: 20px; margin-top: 16px;
}
.badge { font-size: 24px; font-weight: 800; }
.small { color:#69707d; font-size:14px; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
<h1>🛡️ VERITAS</h1>
<p>Understand. Verify. Trust.</p>
</div>
""", unsafe_allow_html=True)

st.write("Assess suspicious digital content using a coordinated multi-agent analysis.")

left, right = st.columns([1, 1])

with left:
    input_type = st.selectbox("Input type", ["Text / Message", "URL"])
    if input_type == "Text / Message":
        user_input = st.text_area(
            "Paste the suspicious message",
            height=250,
            placeholder="Example: URGENT! Your account will be suspended today. Verify immediately..."
        )
    else:
        user_input = st.text_input(
            "Enter URL",
            placeholder="https://example.com"
        )

with right:
    st.markdown("### What VERITAS checks")
    st.markdown("""
    - **Content** — meaning and suspicious signals
    - **Identity** — claimed organisation/sender consistency
    - **Risk** — urgency, manipulation and sensitive requests
    - **Evidence** — correlation across findings
    - **Trust** — evidence-based assessment
    - **Safety** — safer next action
    """)

analyze = st.button("🔎 Analyse with VERITAS", type="primary", use_container_width=True)

if analyze:
    if not user_input or not user_input.strip():
        st.warning("Please enter content to analyse.")
        st.stop()

    with st.spinner("VERITAS agents are analysing the content..."):
        try:
            result = run_veritas(user_input.strip(), input_type)
        except Exception as e:
            st.error("The analysis could not be completed.")
            st.code(str(e))
            st.stop()

    st.divider()
    st.subheader("VERITAS Assessment")

    assessment = result.get("assessment", {})
    level = assessment.get("level", "NEEDS VERIFICATION")
    if level == "HIGH RISK":
        icon = "🔴"
    elif level == "LOW RISK":
        icon = "🟢"
    else:
        icon = "🟡"

    st.markdown(f'<div class="card"><div class="badge">{icon} {level}</div>'
                f'<div class="small">Evidence-based assessment — not absolute proof.</div></div>',
                unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Why?")
        for item in assessment.get("reasons", []):
            st.write("• " + item)

    with c2:
        st.markdown("### Safer next action")
        st.info(result.get("safer_action", "Verify independently before acting."))

    with st.expander("View evidence"):
        for item in result.get("evidence", []):
            st.write("• " + item)

    with st.expander("Agent analysis"):
        for name, data in result.get("agent_outputs", {}).items():
            st.markdown(f"**{name}**")
            st.write(data)
