"""COSHH Assistant — upload SDS, see summary, and ask questions (general or document-specific)."""

import io
import streamlit as st

st.markdown("## 🧪 COSHH Assistant")
st.caption("Upload a Safety Data Sheet for substance-specific guidance, or ask general COSHH questions")

# ── Session state ─────────────────────────────────────────────────────
if "sds_doc" not in st.session_state:
    # {"name": str, "text": str, "structured": dict}
    st.session_state.sds_doc = None
if "coshh_chat" not in st.session_state:
    st.session_state.coshh_chat = []


# ── Text extraction helpers ──────────────────────────────────────────

def extract_pdf_text(file_bytes: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(file_bytes))
    return "\n\n".join((p.extract_text() or "") for p in reader.pages)


def extract_docx_text(file_bytes: bytes) -> str:
    from docx import Document
    doc = Document(io.BytesIO(file_bytes))
    parts = []
    for para in doc.paragraphs:
        if para.text.strip():
            parts.append(para.text)
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    return "\n".join(parts)


def extract_text(uploaded_file) -> str:
    name = uploaded_file.name.lower()
    data = uploaded_file.read()
    if name.endswith(".pdf"):
        return extract_pdf_text(data)
    if name.endswith(".docx"):
        return extract_docx_text(data)
    if name.endswith(".txt"):
        return data.decode("utf-8", errors="replace")
    raise ValueError(f"Unsupported file type: {name}")


# ── Upload box ────────────────────────────────────────────────────────

with st.expander("📄 Upload a Safety Data Sheet (optional)", expanded=st.session_state.sds_doc is None):
    uploaded = st.file_uploader(
        "PDF, DOCX, or TXT",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=False,
        key="sds_uploader",
        label_visibility="collapsed",
    )

    if uploaded and (st.session_state.sds_doc is None or st.session_state.sds_doc["name"] != uploaded.name):
        with st.spinner(f"Reading {uploaded.name}..."):
            try:
                text = extract_text(uploaded)
                if not text.strip():
                    st.error("Could not extract any text from this file. If it's a scanned PDF, OCR is required.")
                else:
                    with st.spinner("AI is extracting COSHH information..."):
                        from riddor_ai import extract_sds
                        structured = extract_sds(text)
                    st.session_state.sds_doc = {
                        "name": uploaded.name,
                        "text": text,
                        "structured": structured,
                    }
                    st.session_state.coshh_chat = []  # reset chat for new doc
                    st.toast(f"Extracted {uploaded.name}", icon="✅")
                    st.rerun()
            except Exception as e:
                st.error(f"Failed to process file: {e}")


# ── Summary card (only if doc uploaded) ──────────────────────────────

doc = st.session_state.sds_doc
if doc:
    structured = doc["structured"]

    if "_raw_response" in structured:
        st.warning("Extraction failed — showing raw model output.")
        with st.expander("Raw response"):
            st.code(structured.get("_raw_response", ""), language=None)
    else:
        product = structured.get("product") or {}
        supplier = structured.get("supplier") or {}
        hazards = structured.get("hazards") or {}

        # Header row
        header_left, header_right = st.columns([3, 1])
        with header_left:
            st.markdown(f"### {product.get('name') or doc['name']}")
            bits = []
            if product.get("code"): bits.append(f"Code: {product['code']}")
            if product.get("cas_number"): bits.append(f"CAS: {product['cas_number']}")
            if structured.get("physical_state"): bits.append(structured["physical_state"])
            if bits: st.caption(" · ".join(bits))
            if supplier.get("name"): st.caption(f"Supplier: {supplier['name']}")
        with header_right:
            signal = hazards.get("signal_word")
            if signal:
                color = "#dc2626" if signal.lower() == "danger" else "#d97706"
                st.markdown(
                    f'<div style="text-align:right"><span style="background:{color};color:white;padding:6px 14px;border-radius:6px;font-weight:700;font-size:14px">{signal.upper()}</span></div>',
                    unsafe_allow_html=True,
                )

        if structured.get("summary"):
            st.info(structured["summary"])

        s1, s2, s3 = st.columns(3)
        with s1:
            st.markdown("**⚠️ Key Hazards**")
            for h in (hazards.get("h_statements") or [])[:5]:
                st.caption(f"• {h}")
            if not hazards.get("h_statements"):
                st.caption("Not specified")
        with s2:
            st.markdown("**🥽 PPE Required**")
            ppe = structured.get("ppe") or {}
            for label, value in [("Eyes", ppe.get("eyes")), ("Hands", ppe.get("hands")), ("Resp.", ppe.get("respiratory"))]:
                if value:
                    st.caption(f"**{label}:** {value}")
            if not any(ppe.values() if ppe else []):
                st.caption("Not specified")
        with s3:
            st.markdown("**📦 Storage & Limits**")
            storage = structured.get("storage") or {}
            limits = structured.get("exposure_limits") or {}
            if storage.get("conditions"): st.caption(f"**Storage:** {storage['conditions']}")
            if limits.get("wel_8h_twa"): st.caption(f"**8h WEL:** {limits['wel_8h_twa']}")
            if limits.get("stel_15min"): st.caption(f"**STEL:** {limits['stel_15min']}")

        with st.expander("View full extraction"):
            st.json(structured, expanded=False)

    # Replace document button
    if st.button("📄 Replace document"):
        st.session_state.sds_doc = None
        st.session_state.coshh_chat = []
        st.rerun()


# ── Chat (always visible) ────────────────────────────────────────────

st.markdown("---")
if doc:
    st.markdown(f"### 💬 Ask questions about **{doc['name']}**")
else:
    st.markdown("### 💬 Ask a COSHH question")
    st.caption("No document uploaded — answering general COSHH questions. Upload an SDS above for substance-specific guidance.")


def _get_answer(messages: list[dict]) -> str:
    """Route to doc-specific or general COSHH chat depending on whether a doc is loaded."""
    if doc:
        from riddor_ai import sds_chat
        return sds_chat(messages, doc["text"], doc["structured"])
    else:
        from riddor_ai import coshh_chat
        return coshh_chat(messages)


# Example prompts on empty chat
if not st.session_state.coshh_chat:
    if doc:
        EXAMPLES = [
            "What PPE do I need?",
            "First aid for eye contact?",
            "How should this be stored?",
            "Is this flammable?",
        ]
    else:
        EXAMPLES = [
            "What is COSHH?",
            "What's the difference between WEL and STEL?",
            "When do I need an SDS?",
            "What does GHS07 mean?",
        ]
    cols = st.columns(2)
    for i, q in enumerate(EXAMPLES):
        with cols[i % 2]:
            if st.button(q, key=f"sds_ex_{i}", use_container_width=True):
                st.session_state.coshh_chat.append({"role": "user", "content": q})
                with st.spinner("Thinking..."):
                    try:
                        ans = _get_answer(st.session_state.coshh_chat)
                        st.session_state.coshh_chat.append({"role": "assistant", "content": ans})
                    except Exception as e:
                        st.session_state.coshh_chat.append({"role": "assistant", "content": f"Error: {e}"})
                st.rerun()

# Chat history
for msg in st.session_state.coshh_chat:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input — always visible
if prompt := st.chat_input("Ask about COSHH..."):
    st.session_state.coshh_chat.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                ans = _get_answer(st.session_state.coshh_chat)
                st.markdown(ans)
                st.session_state.coshh_chat.append({"role": "assistant", "content": ans})
            except Exception as e:
                m = f"Error: {e}"
                st.markdown(m)
                st.session_state.coshh_chat.append({"role": "assistant", "content": m})

if st.session_state.coshh_chat:
    if st.button("🗑️ Clear conversation"):
        st.session_state.coshh_chat = []
        st.rerun()

st.caption("⚠️ AI-assisted summary — always verify against the original SDS before making safety decisions")
