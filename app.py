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
    /* Clean up default Streamlit styling */
    .stApp { background-color: var(--background-color); }
    section[data-testid="stSidebar"] {
        background-color: #0f172a;
        border-right: 1px solid #1e293b;
    }
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown li,
    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: #e2e8f0;
    }
    section[data-testid="stSidebar"] .stMarkdown a { color: #60a5fa; }
    section[data-testid="stSidebar"] hr { border-color: #1e293b; }

    /* Metric cards */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    @media (prefers-color-scheme: dark) {
        [data-testid="stMetric"] {
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border-color: #334155;
        }
    }

    /* Badge styles */
    .badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 600;
        line-height: 20px;
    }
    .badge-red { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }
    .badge-orange { background: #fff7ed; color: #ea580c; border: 1px solid #fed7aa; }
    .badge-amber { background: #fffbeb; color: #d97706; border: 1px solid #fde68a; }
    .badge-blue { background: #eff6ff; color: #2563eb; border: 1px solid #bfdbfe; }
    .badge-purple { background: #f5f3ff; color: #7c3aed; border: 1px solid #c4b5fd; }
    .badge-green { background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; }
    .badge-gray { background: #f9fafb; color: #6b7280; border: 1px solid #e5e7eb; }
    .badge-dark { background: #111827; color: #ffffff; }

    /* Urgency text */
    .urgency-overdue { color: #dc2626; font-weight: 700; }
    .urgency-soon { color: #d97706; font-weight: 600; }
    .urgency-ok { color: #16a34a; }

    /* Card containers */
    .info-card {
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 12px;
        background: white;
    }
    @media (prefers-color-scheme: dark) {
        .info-card { background: #1e293b; border-color: #334155; }
        .badge-red { background: #450a0a; color: #fca5a5; border-color: #7f1d1d; }
        .badge-orange { background: #431407; color: #fdba74; border-color: #7c2d12; }
        .badge-amber { background: #451a03; color: #fcd34d; border-color: #78350f; }
        .badge-blue { background: #172554; color: #93c5fd; border-color: #1e3a5f; }
        .badge-purple { background: #2e1065; color: #c4b5fd; border-color: #3b0764; }
        .badge-green { background: #052e16; color: #86efac; border-color: #14532d; }
        .badge-gray { background: #1f2937; color: #9ca3af; border-color: #374151; }
    }

    /* Chat messages */
    .chat-user {
        background: #2563eb;
        color: white;
        border-radius: 18px 18px 4px 18px;
        padding: 12px 16px;
        margin: 8px 0;
        max-width: 80%;
        margin-left: auto;
    }
    .chat-assistant {
        background: #f1f5f9;
        color: #1e293b;
        border-radius: 18px 18px 18px 4px;
        padding: 12px 16px;
        margin: 8px 0;
        max-width: 80%;
    }
    @media (prefers-color-scheme: dark) {
        .chat-assistant { background: #1e293b; color: #e2e8f0; }
    }

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
    st.caption("⚠️ AI-assisted — always verify critical decisions with HSE directly")

# ── Page navigation ───────────────────────────────────────────────────
pg = st.navigation([
    st.Page("pages/1_Dashboard.py", title="Case Monitor", icon="📊"),
    st.Page("pages/2_Report_Incident.py", title="Report Incident", icon="📝"),
    st.Page("pages/3_Archive.py", title="Past Reports", icon="📁"),
    st.Page("pages/4_AI_Assistant.py", title="AI Assistant", icon="💬"),
])
pg.run()
