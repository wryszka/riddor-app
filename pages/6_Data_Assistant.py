"""Data Assistant — answers questions about the app's actual incidents and SDSs."""

import streamlit as st

st.markdown("## 📚 Data Assistant")
st.caption("Ask questions about your incidents, archive, and uploaded COSHH safety data sheets")

# Init session state
if "data_chat_messages" not in st.session_state:
    st.session_state.data_chat_messages = []

# ── Show what data is available ──────────────────────────────────────
incidents = list(st.session_state.get("incidents", {}).values())
sds_documents = st.session_state.get("sds_documents", {})

c1, c2, c3 = st.columns(3)
with c1:
    open_count = sum(1 for i in incidents if i.get("status") in ("open", "investigating", "pending_report"))
    st.metric("Open Cases", open_count)
with c2:
    submitted_count = sum(1 for i in incidents if i.get("status") == "submitted")
    st.metric("Submitted to HSE", submitted_count)
with c3:
    st.metric("COSHH Documents", len(sds_documents))

st.markdown("---")

# ── Welcome / examples on empty state ────────────────────────────────
if not st.session_state.data_chat_messages:
    st.markdown("""
<div style="text-align:center;padding:20px 20px 10px;">
    <div style="font-size:48px;margin-bottom:12px;">📚</div>
    <h3>Ask about your data</h3>
    <p style="color:#6b7280;">I can search across your incidents, archive, and uploaded COSHH safety data sheets to answer specific questions about your data.</p>
</div>
    """, unsafe_allow_html=True)

    EXAMPLES = [
        "Which cases are overdue and by how much?",
        "How many incidents has each department had?",
        "Tell me about the kitchen burns case",
        "Are there any open cases involving falls?",
        "What's the most common incident type?",
        "Which cases need to be submitted to HSE soon?",
    ]
    if sds_documents:
        EXAMPLES = [
            "Which chemicals on file need respiratory PPE?",
            "What's the highest hazard chemical we have on file?",
        ] + EXAMPLES

    st.markdown("**Try asking:**")
    cols = st.columns(2)
    for i, q in enumerate(EXAMPLES[:6]):
        with cols[i % 2]:
            if st.button(q, key=f"data_ex_{i}", use_container_width=True):
                st.session_state.data_chat_messages.append({"role": "user", "content": q})
                with st.spinner("Searching your data..."):
                    try:
                        from riddor_ai import data_chat
                        ans = data_chat(
                            st.session_state.data_chat_messages,
                            incidents,
                            st.session_state.get("actions", []),
                            sds_documents,
                        )
                        st.session_state.data_chat_messages.append({"role": "assistant", "content": ans})
                    except Exception as e:
                        st.session_state.data_chat_messages.append({"role": "assistant", "content": f"Error: {e}"})
                st.rerun()

# ── Chat history ─────────────────────────────────────────────────────
for msg in st.session_state.data_chat_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Input ────────────────────────────────────────────────────────────
if prompt := st.chat_input("Ask about your incidents and COSHH documents..."):
    st.session_state.data_chat_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Searching your data..."):
            try:
                from riddor_ai import data_chat
                ans = data_chat(
                    st.session_state.data_chat_messages,
                    incidents,
                    st.session_state.get("actions", []),
                    sds_documents,
                )
                st.markdown(ans)
                st.session_state.data_chat_messages.append({"role": "assistant", "content": ans})
            except Exception as e:
                msg = f"Error: {e}"
                st.markdown(msg)
                st.session_state.data_chat_messages.append({"role": "assistant", "content": msg})

if st.session_state.data_chat_messages:
    if st.button("🗑️ Clear conversation"):
        st.session_state.data_chat_messages = []
        st.rerun()

st.caption("⚠️ Answers grounded in your app's data — verify against original sources for critical decisions")
