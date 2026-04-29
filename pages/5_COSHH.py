"""COSHH Safety Data Sheet — upload, summary, and Q&A on one page."""

import io
import streamlit as st

st.markdown("## 🧪 COSHH Assistant")
st.caption("Upload a Safety Data Sheet (SDS) and ask questions about it")

# ── Session state ─────────────────────────────────────────────────────
if "sds_doc" not in st.session_state:
    # Single active SDS: {"name": str, "text": str, "structured": dict, "chat": list}
    st.session_state.sds_doc = None


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


# ── Upload ────────────────────────────────────────────────────────────

uploaded = st.file_uploader(
    "Upload an SDS (PDF, DOCX, or TXT)",
    type=["pdf", "docx", "txt"],
    accept_multiple_files=False,
    key="sds_uploader",
)

# Process new upload
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
                    "chat": [],
                }
                st.toast(f"Extracted {uploaded.name}", icon="✅")
                st.rerun()
        except Exception as e:
            st.error(f"Failed to process file: {e}")


# ── If no doc, show prompt and stop ──────────────────────────────────
if st.session_state.sds_doc is None:
    st.info("👆 Upload a Safety Data Sheet to get started.")
    st.stop()


# ── Summary card ─────────────────────────────────────────────────────

doc = st.session_state.sds_doc
structured = doc["structured"]

st.markdown("---")

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

    # Compact summary in 3 columns
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

# ── Chat ─────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown("### 💬 Ask questions about this document")

# Examples on empty chat
if not doc["chat"]:
    EXAMPLES = [
        "What PPE do I need to use this safely?",
        "First aid for eye contact?",
        "Is this flammable?",
        "How should this be stored?",
    ]
    cols = st.columns(2)
    for i, q in enumerate(EXAMPLES):
        with cols[i % 2]:
            if st.button(q, key=f"sds_ex_{i}", use_container_width=True):
                doc["chat"].append({"role": "user", "content": q})
                with st.spinner("Reading the document..."):
                    try:
                        from riddor_ai import sds_chat
                        ans = sds_chat(doc["chat"], doc["text"], doc["structured"])
                        doc["chat"].append({"role": "assistant", "content": ans})
                    except Exception as e:
                        doc["chat"].append({"role": "assistant", "content": f"Error: {e}"})
                st.rerun()

# Chat history
for msg in doc["chat"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input(f"Ask about {doc['name']}..."):
    doc["chat"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Reading the document..."):
            try:
                from riddor_ai import sds_chat
                ans = sds_chat(doc["chat"], doc["text"], doc["structured"])
                st.markdown(ans)
                doc["chat"].append({"role": "assistant", "content": ans})
            except Exception as e:
                m = f"Error: {e}"
                st.markdown(m)
                doc["chat"].append({"role": "assistant", "content": m})

# Footer actions
fc1, fc2 = st.columns([1, 1])
with fc1:
    if doc["chat"]:
        if st.button("🗑️ Clear conversation", use_container_width=True):
            doc["chat"] = []
            st.rerun()
with fc2:
    if st.button("📄 Replace document", use_container_width=True):
        st.session_state.sds_doc = None
        st.rerun()

st.caption("⚠️ AI-assisted summary — always verify against the original SDS before making safety decisions")
