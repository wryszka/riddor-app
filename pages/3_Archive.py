"""Past Reports Archive — searchable history with trend charts."""

import streamlit as st
import pandas as pd
import plotly.express as px
from riddor_data import INCIDENT_TYPE_CONFIG, STATUS_CONFIG

st.markdown("## 📁 Past Reports")
st.caption("Historical RIDDOR submissions and incident trends")

all_incidents = list(st.session_state.incidents.values())

if not all_incidents:
    st.info("No incidents recorded yet.")
    st.stop()

# ── Build DataFrame ───────────────────────────────────────────────────
df = pd.DataFrame(all_incidents)
df["type_label"] = df["incident_type"].map(lambda x: INCIDENT_TYPE_CONFIG.get(x, {}).get("label", x))
df["status_label"] = df["status"].map(lambda x: STATUS_CONFIG.get(x, {}).get("label", x))
df["incident_date"] = pd.to_datetime(df["incident_date"])

# ── Trend Charts ──────────────────────────────────────────────────────
c1, c2 = st.columns(2)

with c1:
    st.markdown("#### Incidents by Type")
    type_counts = df["type_label"].value_counts().reset_index()
    type_counts.columns = ["Type", "Count"]
    color_map = {v["label"]: v["color"] for v in INCIDENT_TYPE_CONFIG.values()}
    fig = px.pie(
        type_counts, values="Count", names="Type",
        color="Type", color_discrete_map=color_map,
        hole=0.4,
    )
    fig.update_layout(
        margin=dict(t=20, b=20, l=20, r=20),
        height=300,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.3),
    )
    fig.update_traces(textposition="inside", textinfo="value+label")
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.markdown("#### Incidents by Department")
    dept_counts = df["department"].value_counts().reset_index()
    dept_counts.columns = ["Department", "Count"]
    fig2 = px.bar(
        dept_counts, x="Count", y="Department", orientation="h",
        color_discrete_sequence=["#2563eb"],
    )
    fig2.update_layout(
        margin=dict(t=20, b=20, l=20, r=20),
        height=300,
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

# ── Filters ───────────────────────────────────────────────────────────
c1, c2, c3 = st.columns(3)
search = c1.text_input("🔍 Search", placeholder="Name, reference, or description...")
type_filter = c2.selectbox(
    "Incident Type",
    ["All"] + [v["label"] for v in INCIDENT_TYPE_CONFIG.values()],
)
dept_filter = c3.selectbox(
    "Department",
    ["All"] + sorted(df["department"].unique().tolist()),
)

# Apply filters
filtered = df.copy()
if search:
    q = search.lower()
    filtered = filtered[
        filtered["person_name"].str.lower().str.contains(q, na=False)
        | filtered["description"].str.lower().str.contains(q, na=False)
        | filtered["reference"].str.lower().str.contains(q, na=False)
    ]
if type_filter != "All":
    filtered = filtered[filtered["type_label"] == type_filter]
if dept_filter != "All":
    filtered = filtered[filtered["department"] == dept_filter]

filtered = filtered.sort_values("incident_date", ascending=False)

st.caption(f"Showing {len(filtered)} of {len(df)} incidents")

# ── Results ───────────────────────────────────────────────────────────
TYPE_BADGE_CLASS = {
    "death": "badge-dark",
    "specified_injury": "badge-red",
    "over_7_day": "badge-orange",
    "non_worker_hospital": "badge-purple",
    "occupational_disease": "badge-blue",
    "dangerous_occurrence": "badge-amber",
    "not_reportable": "badge-gray",
}

STATUS_BADGE_CLASS = {
    "open": "badge-blue",
    "investigating": "badge-amber",
    "pending_report": "badge-orange",
    "submitted": "badge-green",
    "closed": "badge-gray",
}

for _, row in filtered.iterrows():
    type_cls = TYPE_BADGE_CLASS.get(row["incident_type"], "badge-gray")
    type_label = INCIDENT_TYPE_CONFIG.get(row["incident_type"], {}).get("label", row["incident_type"])
    status_cls = STATUS_BADGE_CLASS.get(row["status"], "badge-gray")
    status_label = STATUS_CONFIG.get(row["status"], {}).get("label", row["status"])

    with st.container(border=True):
        c1, c2, c3, c4, c5 = st.columns([1.5, 1, 1.5, 1, 1])
        with c1:
            st.markdown(f"**{row['reference']}**")
            st.caption(row["incident_date"].strftime("%d %b %Y"))
        with c2:
            st.markdown(f'<span class="badge {type_cls}">{type_label}</span>', unsafe_allow_html=True)
        with c3:
            st.markdown(f"**{row['person_name']}**")
            st.caption(row["department"])
        with c4:
            st.markdown(f'<span class="badge {status_cls}">{status_label}</span>', unsafe_allow_html=True)
        with c5:
            hse_ref = row.get("hse_reference")
            if hse_ref:
                st.caption(f"HSE: {hse_ref}")
            else:
                st.caption("—")

        with st.expander("View Full Report"):
            st.markdown(f"**Description:** {row['description']}")
            if row.get("injury_details"):
                st.markdown(f"**Injury Details:** {row['injury_details']}")
            if row.get("ai_reasoning"):
                st.markdown(f"**AI Assessment:** {row['ai_reasoning']}")

            cls = row.get("ai_classification")
            if cls and isinstance(cls, dict):
                if cls.get("key_factors"):
                    st.markdown("**Key Factors:** " + ", ".join(cls["key_factors"]))
                if cls.get("actions_required"):
                    st.markdown("**Actions Required:**")
                    for a in cls["actions_required"]:
                        st.markdown(f"- {a}")
