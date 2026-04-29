"""COSHH Assistant — upload SDS, see Condensed COSHH Assessment, download PDF, ask questions."""

import io
import streamlit as st

st.markdown("## 🧪 COSHH Assistant")
st.caption("Upload a Safety Data Sheet for substance-specific guidance, or ask general COSHH questions")

# ── Session state ─────────────────────────────────────────────────────
if "sds_doc" not in st.session_state:
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

with st.expander("📄 Upload a Safety Data Sheet", expanded=st.session_state.sds_doc is None):
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
                    with st.spinner("AI is generating the Condensed COSHH Assessment..."):
                        from riddor_ai import extract_sds
                        structured = extract_sds(text)
                    st.session_state.sds_doc = {
                        "name": uploaded.name,
                        "text": text,
                        "structured": structured,
                    }
                    st.session_state.coshh_chat = []
                    st.toast(f"Assessment generated for {uploaded.name}", icon="✅")
                    st.rerun()
            except Exception as e:
                st.error(f"Failed to process file: {e}")


# ── Condensed COSHH Assessment display ───────────────────────────────

doc = st.session_state.sds_doc
if doc:
    structured = doc["structured"]
    product = structured.get("product") or {}
    hazards = structured.get("hazards") or {}
    ppe = structured.get("ppe") or {}
    first_aid = structured.get("first_aid") or {}
    storage = structured.get("storage") or {}

    # Header with download button
    h1, h2 = st.columns([3, 1])
    with h1:
        st.markdown("### 📋 Condensed COSHH Assessment")
    with h2:
        try:
            from coshh_pdf import build_coshh_pdf
            pdf_bytes = build_coshh_pdf(structured, doc["name"])
            product_name = product.get("name") or doc["name"].rsplit(".", 1)[0]
            safe_name = "".join(c if c.isalnum() else "_" for c in product_name)[:50]
            st.download_button(
                "⬇️ Download PDF",
                data=pdf_bytes,
                file_name=f"COSHH_Assessment_{safe_name}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"PDF generation failed: {e}")

    if "_raw_response" in structured:
        st.warning("Extraction failed — showing raw model output.")
        with st.expander("Raw response"):
            st.code(structured.get("_raw_response", ""), language=None)
    else:
        # ── Container styled to look like an assessment document ────
        st.markdown(
            """<style>
            .coshh-doc { border: 1px solid rgba(128,128,128,0.25); border-radius: 12px; padding: 24px 28px; background: rgba(248,250,252,0.5); }
            @media (prefers-color-scheme: dark) { .coshh-doc { background: rgba(30,41,59,0.4); } }
            .coshh-row { margin-bottom: 6px; }
            .coshh-label { font-weight: 700; color: var(--text-color); display: inline-block; min-width: 170px; }
            .coshh-section-title { font-weight: 700; color: #2563eb; margin-top: 14px; margin-bottom: 4px; }
            .coshh-risk { display: inline-block; padding: 6px 16px; border-radius: 6px; font-weight: 700; color: white; font-size: 14px; }
            .coshh-risk.low { background: #16a34a; }
            .coshh-risk.medium { background: #d97706; }
            .coshh-risk.high { background: #dc2626; }
            </style>""",
            unsafe_allow_html=True,
        )

        with st.container():
            st.markdown('<div class="coshh-doc">', unsafe_allow_html=True)

            def row(label: str, value):
                if value:
                    st.markdown(f'<div class="coshh-row"><span class="coshh-label">{label}:</span> {value}</div>', unsafe_allow_html=True)

            def section(title: str, body):
                if not body:
                    return
                st.markdown(f'<div class="coshh-section-title">{title}:</div>', unsafe_allow_html=True)
                if isinstance(body, list):
                    items = [b for b in body if b]
                    if items:
                        st.markdown("\n".join(f"- {x}" for x in items))
                elif isinstance(body, dict):
                    items = [(k, v) for k, v in body.items() if v]
                    if items:
                        for k, v in items:
                            st.markdown(f"- **{k}:** {v}")
                else:
                    st.markdown(str(body))

            # Header rows
            row("Product Name", product.get("name") or doc["name"])
            row("Use of Product", structured.get("use_of_product"))
            row("Form", structured.get("form") or structured.get("appearance"))
            row("pH", structured.get("ph"))

            # Sections
            section("Method of Application", structured.get("method_of_application"))

            clp = structured.get("clp_hazard_summary")
            if not clp and hazards.get("h_statements"):
                clp = "; ".join(hazards["h_statements"][:3])
            section("CLP Hazard Information", clp)

            routes = structured.get("routes_of_entry") or []
            if routes:
                section("Routes of Entry", ", ".join(routes))

            ppe_items = []
            for label, value in [
                ("Hands", ppe.get("hands")),
                ("Eyes", ppe.get("eyes")),
                ("Respiratory", ppe.get("respiratory")),
                ("Body", ppe.get("body")),
            ]:
                if value:
                    ppe_items.append(f"**{label}:** {value}")
            section("Mandatory PPE", ppe_items)

            fa_dict = {}
            if first_aid.get("skin_contact"): fa_dict["Skin contact"] = first_aid["skin_contact"]
            if first_aid.get("eye_contact"): fa_dict["Eye contact"] = first_aid["eye_contact"]
            if first_aid.get("inhalation"): fa_dict["Inhalation"] = first_aid["inhalation"]
            if first_aid.get("ingestion"): fa_dict["Ingestion"] = first_aid["ingestion"]
            section("First Aid Measures", fa_dict)

            section("Spillage Procedure", structured.get("spill_response"))

            storage_parts = []
            if storage.get("conditions"): storage_parts.append(storage["conditions"])
            if storage.get("container"): storage_parts.append(f"Container: {storage['container']}")
            if storage.get("incompatible_materials"): storage_parts.append(f"Keep away from: {storage['incompatible_materials']}")
            section("Handling and Storage", " ".join(storage_parts) if storage_parts else None)

            section("General Precautions", structured.get("general_precautions"))
            section("Disposal", structured.get("disposal"))

            # Risk rating
            rating = (structured.get("risk_rating") or "LOW").upper()
            cls = "low" if "LOW" in rating else ("high" if "HIGH" in rating else "medium")
            st.markdown(
                f'<div class="coshh-section-title">Risk Rating (after control measures):</div>'
                f'<span class="coshh-risk {cls}">{rating}</span>',
                unsafe_allow_html=True,
            )

            st.markdown("</div>", unsafe_allow_html=True)

    if st.button("📄 New document"):
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
    if doc:
        from riddor_ai import sds_chat
        return sds_chat(messages, doc["text"], doc["structured"])
    else:
        from riddor_ai import coshh_chat
        return coshh_chat(messages)


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

for msg in st.session_state.coshh_chat:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

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

st.caption("⚠️ AI-generated assessment — always verify against the original SDS before making safety decisions")
