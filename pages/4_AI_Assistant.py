"""AI Assistant — RIDDOR expert with full visibility of the app's data."""

import streamlit as st

st.markdown("## 💬 AI Assistant")
st.caption("Ask about RIDDOR regulations or your own incidents and chemicals on file")

# ── Init state ────────────────────────────────────────────────────────
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

# ── Gather context the assistant has access to ───────────────────────
incidents = list(st.session_state.get("incidents", {}).values())
sds_doc = st.session_state.get("sds_doc")
sds_documents = {sds_doc["name"]: {"structured": sds_doc["structured"]}} if sds_doc else {}

# ── Empty state with examples ────────────────────────────────────────
if not st.session_state.chat_messages:
    st.markdown("""
<div style="text-align: center; padding: 30px 20px 10px;">
    <div style="font-size: 48px; margin-bottom: 12px;">🛡️</div>
    <h3>RIDDOR Expert + Data Assistant</h3>
    <p style="color: #6b7280;">
        Ask about RIDDOR regulations, classification questions, or your own incidents and chemicals on file.
    </p>
</div>
    """, unsafe_allow_html=True)

    REGULATION_EXAMPLES = [
        "Is a broken finger RIDDOR reportable?",
        "What counts as a dangerous occurrence?",
        "How do I calculate the 7-day absence period?",
    ]
    DATA_EXAMPLES = [
        "Which cases are overdue and by how much?",
        "How many incidents has each department had?",
        "Tell me about the kitchen burns case",
    ]

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**About RIDDOR rules**")
        for i, q in enumerate(REGULATION_EXAMPLES):
            if st.button(q, key=f"reg_ex_{i}", use_container_width=True):
                st.session_state._pending_q = q
                st.rerun()
    with c2:
        st.markdown("**About your data**")
        for i, q in enumerate(DATA_EXAMPLES):
            if st.button(q, key=f"data_ex_{i}", use_container_width=True):
                st.session_state._pending_q = q
                st.rerun()


def _send(prompt: str):
    """Send a message to the data-aware assistant."""
    st.session_state.chat_messages.append({"role": "user", "content": prompt})
    try:
        from riddor_ai import data_chat
        ans = data_chat(
            st.session_state.chat_messages,
            incidents,
            st.session_state.get("actions", []),
            sds_documents,
        )
        st.session_state.chat_messages.append({"role": "assistant", "content": ans})
    except Exception as e:
        st.session_state.chat_messages.append({"role": "assistant", "content": f"Sorry, I encountered an error: {e}"})


# Process pending example button click
if "_pending_q" in st.session_state:
    q = st.session_state.pop("_pending_q")
    with st.spinner("Thinking..."):
        _send(q)
    st.rerun()

# ── Chat history ─────────────────────────────────────────────────────
for msg in st.session_state.chat_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Input ────────────────────────────────────────────────────────────
if prompt := st.chat_input("Ask about RIDDOR or your data..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            _send(prompt)
            st.markdown(st.session_state.chat_messages[-1]["content"])

if st.session_state.chat_messages:
    if st.button("🗑️ Clear Chat"):
        st.session_state.chat_messages = []
        st.rerun()

st.caption("⚠️ AI-assisted — always verify critical decisions with HSE directly")
