"""AI Chat Assistant — RIDDOR expert conversational interface."""

import streamlit as st

st.markdown("## 💬 AI Assistant")
st.caption("Ask questions about RIDDOR regulations, incident classification, and reporting requirements")

# ── Example questions ─────────────────────────────────────────────────
EXAMPLES = [
    "An employee slipped and broke their wrist yesterday — is this RIDDOR reportable?",
    "A visitor fainted in reception and went to hospital as a precaution — do I need to report?",
    "What counts as a dangerous occurrence?",
    "How do I calculate the 7-day absence period?",
    "What's the difference between a specified injury and an over-7-day injury?",
    "A contractor cut their finger and needed stitches — is this reportable?",
]

# Initialise chat
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

# ── Layout: chat + reference sidebar ──────────────────────────────────
chat_col, ref_col = st.columns([3, 1])

with ref_col:
    st.markdown("#### Quick Reference")
    st.markdown("""
**HSE Reporting**
- Online: hse.gov.uk/riddor
- Phone: 0345 300 9923

**Key Deadlines**
- Deaths/Specified: Without delay
- Over-7-day: Within 15 days
- Diseases: Without delay

**Records**: Min 3 years
    """)

    st.markdown("---")
    st.markdown("#### Try asking...")
    for q in EXAMPLES:
        if st.button(f'"{q}"', key=f"ex_{hash(q)}", use_container_width=True):
            st.session_state.chat_messages.append({"role": "user", "content": q})
            with st.spinner("Thinking..."):
                try:
                    from riddor_ai import chat_response
                    resp = chat_response(st.session_state.chat_messages)
                    st.session_state.chat_messages.append({"role": "assistant", "content": resp})
                except Exception as e:
                    st.session_state.chat_messages.append({
                        "role": "assistant",
                        "content": f"Sorry, I encountered an error: {e}",
                    })
            st.rerun()

with chat_col:
    # Welcome message if no history
    if not st.session_state.chat_messages:
        st.markdown("""
<div style="text-align: center; padding: 40px 20px;">
    <div style="font-size: 48px; margin-bottom: 16px;">🛡️</div>
    <h3>RIDDOR Expert Assistant</h3>
    <p style="color: #6b7280; max-width: 400px; margin: 0 auto;">
        I'm here to help you understand RIDDOR 2013 regulations. Ask me about
        incident classification, reporting deadlines, or any workplace health & safety question.
    </p>
</div>
        """, unsafe_allow_html=True)

    # Display messages
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input("Ask about RIDDOR regulations..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    from riddor_ai import chat_response
                    resp = chat_response(st.session_state.chat_messages)
                    st.markdown(resp)
                    st.session_state.chat_messages.append({"role": "assistant", "content": resp})
                except Exception as e:
                    error_msg = f"Sorry, I encountered an error connecting to the AI model: {e}"
                    st.markdown(error_msg)
                    st.session_state.chat_messages.append({"role": "assistant", "content": error_msg})

    # Clear chat button
    if st.session_state.chat_messages:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.chat_messages = []
            st.rerun()

st.caption("⚠️ AI-assisted guidance — always verify critical decisions with HSE directly")
