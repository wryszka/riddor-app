"""Report an Incident — AI-powered RIDDOR classification."""

import streamlit as st
import uuid
from datetime import date, datetime, timedelta
from riddor_data import INCIDENT_TYPE_CONFIG

st.markdown("## 📝 Report an Incident")
st.caption("Describe a workplace incident for AI-powered RIDDOR classification")

# ── Step tracking ─────────────────────────────────────────────────────
if "report_step" not in st.session_state:
    st.session_state.report_step = "input"
if "classification" not in st.session_state:
    st.session_state.classification = None

# Progress indicator
step = st.session_state.report_step
steps = {"input": 0, "result": 1, "saved": 2}
cols = st.columns(3)
labels = ["1. Describe Incident", "2. AI Classification", "3. Save Case"]
for i, (c, label) in enumerate(zip(cols, labels)):
    if i <= steps.get(step, 0):
        c.markdown(f"**🔵 {label}**")
    else:
        c.markdown(f"⚪ {label}")
st.markdown("---")

# ── Step 1: Input ─────────────────────────────────────────────────────
if step == "input":
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("### Incident Description")
        description = st.text_area(
            "What happened?",
            placeholder="E.g., An employee slipped on a wet floor in the warehouse and broke their wrist. They were taken to hospital by ambulance...",
            height=200,
            key="report_description",
        )
        st.markdown("### Upload Documents")
        uploaded = st.file_uploader(
            "Drag and drop accident forms, photos, or documents",
            type=["pdf", "png", "jpg", "jpeg", "doc", "docx", "txt"],
            accept_multiple_files=True,
            key="report_files",
        )
        if uploaded:
            for f in uploaded:
                st.caption(f"📎 {f.name} ({f.size / 1024:.0f} KB)")

    with col_right:
        st.markdown("### Incident Details")
        incident_date = st.date_input("Incident Date", value=date.today(), key="report_date")
        person_type = st.selectbox("Person Type", ["Worker / Employee", "Non-Worker / Visitor"], key="report_person_type")
        person_name = st.text_input("Injured Person's Name", key="report_person_name")

        c1, c2 = st.columns(2)
        department = c1.text_input("Department", key="report_dept")
        location = c2.text_input("Location", key="report_location")

        injury_details = st.text_area("Injury Details", placeholder="Type and severity of injury, treatment given...", height=100, key="report_injury")
        reporter_name = st.text_input("Your Name (Reporter)", key="report_reporter")

    st.markdown("---")
    if st.button("🧠 Classify with AI", type="primary", disabled=not description, use_container_width=True):
        full_desc = "\n".join(filter(None, [
            description,
            f"Person involved: {person_name}" if person_name else None,
            f"Person type: {'worker' if 'Worker' in person_type else 'non_worker'}",
            f"Department: {department}" if department else None,
            f"Location: {location}" if location else None,
            f"Injury details: {injury_details}" if injury_details else None,
        ]))

        with st.spinner("AI is analysing the incident against RIDDOR 2013 regulations..."):
            try:
                from riddor_ai import classify_incident
                result = classify_incident(full_desc)
                st.session_state.classification = result
                st.session_state.report_step = "result"
                st.rerun()
            except Exception as e:
                st.error(f"Classification failed: {e}")

# ── Step 2: Classification Result ─────────────────────────────────────
elif step == "result":
    cls = st.session_state.classification
    if not cls:
        st.session_state.report_step = "input"
        st.rerun()

    is_reportable = cls.get("is_reportable", False)

    # Main classification card
    if is_reportable:
        st.error(f"### ⚠️ RIDDOR Reportable — {cls.get('category_label', 'Unknown')}")
    else:
        st.success("### ✅ Not Reportable Under RIDDOR")

    st.markdown(f"**Confidence:** {cls.get('confidence', 'unknown').upper()}")
    st.markdown(f"**Reasoning:** {cls.get('reasoning', '')}")

    if is_reportable:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("#### ⏰ Reporting Deadline")
            st.info(cls.get("reporting_deadline", "N/A"))
        with c2:
            st.markdown("#### 🌐 Reporting Method")
            st.info(cls.get("reporting_method", "N/A"))
        with c3:
            st.markdown("#### 📋 Records to Keep")
            for r in cls.get("records_to_keep", []):
                st.markdown(f"- {r}")

    st.markdown("---")

    # Key factors
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Key Factors")
        for f in cls.get("key_factors", []):
            st.markdown(f"🔹 {f}")
    with c2:
        st.markdown("#### Required Actions")
        for a in cls.get("actions_required", []):
            st.markdown(f"✅ {a}")

    st.markdown("---")

    # Override option
    with st.expander("🔧 Override Classification"):
        override_cat = st.selectbox(
            "Change category",
            options=list(INCIDENT_TYPE_CONFIG.keys()),
            index=list(INCIDENT_TYPE_CONFIG.keys()).index(cls.get("category", "not_reportable")),
            format_func=lambda x: INCIDENT_TYPE_CONFIG[x]["label"],
            key="override_select",
        )
        if st.button("Apply Override"):
            cfg = INCIDENT_TYPE_CONFIG[override_cat]
            st.session_state.classification["category"] = override_cat
            st.session_state.classification["category_label"] = cfg["label"]
            st.session_state.classification["is_reportable"] = override_cat != "not_reportable"
            st.rerun()

    # Action buttons
    c1, c2 = st.columns(2)
    if c1.button("✅ Accept & Create Case", type="primary", use_container_width=True):
        # Save to session state
        incident_id = str(uuid.uuid4())[:8]
        now = datetime.utcnow().isoformat()
        incident_date_str = st.session_state.get("report_date", date.today()).isoformat()
        category = cls.get("category", "unknown")

        deadline = None
        if category in ("death", "specified_injury", "occupational_disease", "dangerous_occurrence", "non_worker_hospital"):
            deadline = (date.today() + timedelta(days=10)).isoformat()
        elif category == "over_7_day":
            d = datetime.strptime(incident_date_str, "%Y-%m-%d")
            deadline = (d + timedelta(days=15)).strftime("%Y-%m-%d")

        new_incident = {
            "id": f"inc-{incident_id}",
            "reference": f"RIDDOR-{date.today().strftime('%Y%m%d')}-{incident_id[:4].upper()}",
            "created_at": now,
            "incident_date": incident_date_str,
            "incident_type": category,
            "person_name": st.session_state.get("report_person_name", "Unknown"),
            "person_type": "worker" if "Worker" in st.session_state.get("report_person_type", "Worker") else "non_worker",
            "department": st.session_state.get("report_dept", "Unknown"),
            "location": st.session_state.get("report_location", ""),
            "description": st.session_state.get("report_description", ""),
            "injury_details": st.session_state.get("report_injury", ""),
            "ai_classification": cls,
            "ai_reasoning": cls.get("reasoning", ""),
            "manager_override": None,
            "status": "open",
            "reporting_deadline": deadline,
            "hse_reference": None,
            "submitted_at": None,
            "reporter_name": st.session_state.get("report_reporter", ""),
            "absence_days": None,
        }

        st.session_state.incidents[new_incident["id"]] = new_incident
        st.session_state.actions.append({
            "id": str(uuid.uuid4())[:8],
            "incident_id": new_incident["id"],
            "action_type": "created",
            "description": "Incident report created with AI classification",
            "performed_by": st.session_state.get("report_reporter", "System"),
            "timestamp": now,
        })

        st.session_state.report_step = "saved"
        st.session_state.new_ref = new_incident["reference"]
        st.rerun()

    if c2.button("← Go Back & Edit", use_container_width=True):
        st.session_state.report_step = "input"
        st.rerun()

# ── Step 3: Saved ─────────────────────────────────────────────────────
elif step == "saved":
    st.balloons()
    st.success(f"### ✅ Case Created: {st.session_state.get('new_ref', '')}")
    st.markdown("The incident has been saved and is now visible in the **Case Monitor** dashboard.")
    st.markdown("Navigate to the **Case Monitor** tab to view and manage this case.")

    if st.button("📝 Report Another Incident", use_container_width=True):
        st.session_state.report_step = "input"
        st.session_state.classification = None
        st.rerun()
