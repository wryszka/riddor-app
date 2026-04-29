"""RIDDOR Decision Support — Streamlit Application."""

import streamlit as st

st.set_page_config(
    page_title="RIDDOR Decision Support",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS for polished look ──────────────────────────────────────
st.markdown("""
<style>
    /* Sidebar — use Streamlit's own secondary background, don't force dark */
    section[data-testid="stSidebar"] {
        border-right: 1px solid rgba(128,128,128,0.2);
    }

    /* Metric cards */
    [data-testid="stMetric"] {
        border: 1px solid rgba(128,128,128,0.2);
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }

    /* Badge styles — use solid colours that work on any background */
    .badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 600;
        line-height: 20px;
        white-space: nowrap;
    }
    .badge-red { background: #dc2626; color: #ffffff; }
    .badge-orange { background: #ea580c; color: #ffffff; }
    .badge-amber { background: #d97706; color: #ffffff; }
    .badge-blue { background: #2563eb; color: #ffffff; }
    .badge-purple { background: #7c3aed; color: #ffffff; }
    .badge-green { background: #16a34a; color: #ffffff; }
    .badge-gray { background: #6b7280; color: #ffffff; }
    .badge-dark { background: #111827; color: #ffffff; }

    /* Urgency text */
    .urgency-overdue { color: #dc2626; font-weight: 700; }
    .urgency-soon { color: #d97706; font-weight: 600; }
    .urgency-ok { color: #16a34a; }

    /* Hide default decoration */
    .stDeployButton { display: none; }
    header[data-testid="stHeader"] { background: transparent; }
</style>
""", unsafe_allow_html=True)

# ── Initialise session state ──────────────────────────────────────────
if "incidents" not in st.session_state:
    from riddor_data import MOCK_INCIDENTS, MOCK_ACTIONS
    st.session_state.incidents = {i["id"]: i for i in MOCK_INCIDENTS}
    st.session_state.actions = list(MOCK_ACTIONS)
    st.session_state.chat_messages = []

# ── Sidebar ───────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🛡️ RIDDOR")
    st.markdown("##### Decision Support")
    st.markdown("---")

    st.markdown("""
**Quick Reference**

📞 HSE Phone: **0345 300 9923**
🌐 Online: hse.gov.uk/riddor

**Deadlines**
- Deaths/Specified injuries: *Without delay*
- Over-7-day: *Within 15 days*
- Diseases/Occurrences: *Without delay*

**Records**: Keep for 3+ years
    """)
    st.markdown("---")
    if st.button("🔄 Reset Demo Data", use_container_width=True, help="Restore all incidents and chat to their original state"):
        from riddor_data import MOCK_INCIDENTS, MOCK_ACTIONS
        st.session_state.incidents = {i["id"]: i for i in MOCK_INCIDENTS}
        st.session_state.actions = list(MOCK_ACTIONS)
        st.session_state.chat_messages = []
        # Reset Report Incident wizard state
        for k in ("report_step", "classification", "new_ref"):
            st.session_state.pop(k, None)
        # Reset COSHH state
        st.session_state.sds_documents = {}
        st.session_state.active_sds = None
        st.toast("Demo reset to original state", icon="✅")
        st.rerun()
    st.caption("⚠️ AI-assisted — always verify critical decisions with HSE directly")

# ── Page navigation ───────────────────────────────────────────────────
pg = st.navigation([
    st.Page("pages/1_Dashboard.py", title="Case Monitor", icon="📊"),
    st.Page("pages/2_Report_Incident.py", title="Report Incident", icon="📝"),
    st.Page("pages/3_Archive.py", title="Past Reports", icon="📁"),
    st.Page("pages/4_AI_Assistant.py", title="AI Assistant", icon="💬"),
    st.Page("pages/5_COSHH.py", title="COSHH Assistant", icon="🧪"),
])
pg.run()
