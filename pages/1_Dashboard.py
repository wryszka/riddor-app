"""Case Monitor Dashboard — open RIDDOR cases, metrics, urgency tracking."""

import streamlit as st
from datetime import date, timedelta
from riddor_data import INCIDENT_TYPE_CONFIG, STATUS_CONFIG, get_days_remaining

incidents = st.session_state.incidents
all_incidents = list(incidents.values())
today = date.today().isoformat()

# ── Metrics ───────────────────────────────────────────────────────────
open_statuses = {"open", "investigating", "pending_report"}
open_cases = [i for i in all_incidents if i["status"] in open_statuses]
overdue = [i for i in open_cases if i.get("reporting_deadline") and i["reporting_deadline"] < today]
approaching = [
    i for i in open_cases
    if i.get("reporting_deadline")
    and i["reporting_deadline"] >= today
    and i["reporting_deadline"] <= (date.today() + timedelta(days=3)).isoformat()
]
submitted = [i for i in all_incidents if i["status"] == "submitted"]

st.markdown("## 📊 Case Monitor")
st.caption("Track and manage open RIDDOR cases")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Open Cases", len(open_cases))
col2.metric("Approaching Deadline", len(approaching), help="Due within 3 days")
col3.metric("Overdue", len(overdue), delta=f"-{len(overdue)}" if overdue else None, delta_color="inverse")
col4.metric("Submitted to HSE", len(submitted))

st.markdown("---")

# ── Badge helpers ─────────────────────────────────────────────────────
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


def type_badge(t):
    cfg = INCIDENT_TYPE_CONFIG.get(t, {"label": t})
    cls = TYPE_BADGE_CLASS.get(t, "badge-gray")
    return f'<span class="badge {cls}">{cfg["label"]}</span>'


def status_badge(s):
    cfg = STATUS_CONFIG.get(s, {"label": s})
    cls = STATUS_BADGE_CLASS.get(s, "badge-gray")
    return f'<span class="badge {cls}">{cfg["label"]}</span>'


def deadline_html(deadline, status):
    if not deadline or status in ("submitted", "closed"):
        return "—"
    days = get_days_remaining(deadline)
    if days is None:
        return deadline
    if days < 0:
        return f'<span class="urgency-overdue">{deadline}<br/>{abs(days)}d overdue</span>'
    if days <= 3:
        return f'<span class="urgency-soon">{deadline}<br/>{days}d left</span>'
    return f'<span class="urgency-ok">{deadline}<br/>{days}d left</span>'


# ── Open Cases Table ──────────────────────────────────────────────────
if not open_cases:
    st.success("✅ No open cases — all RIDDOR cases have been resolved")
else:
    st.markdown(f"### Open Cases ({len(open_cases)})")

    # Sort: overdue first, then by deadline
    def sort_key(i):
        dl = i.get("reporting_deadline") or "9999-12-31"
        return dl
    open_cases.sort(key=sort_key)

    for inc in open_cases:
        days_left = get_days_remaining(inc.get("reporting_deadline"))
        border_color = "#dc2626" if days_left is not None and days_left < 0 else (
            "#d97706" if days_left is not None and days_left <= 3 else "#e2e8f0"
        )

        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns([1.5, 1, 1.5, 1, 1.5])
            with c1:
                st.markdown(f"**{inc['reference']}**")
                st.caption(inc["incident_date"])
            with c2:
                st.markdown(type_badge(inc["incident_type"]), unsafe_allow_html=True)
            with c3:
                st.markdown(f"**{inc['person_name']}**")
                st.caption(f"{inc['department']} · {inc['person_type'].replace('_', '-')}")
            with c4:
                st.markdown(status_badge(inc["status"]), unsafe_allow_html=True)
            with c5:
                st.markdown(deadline_html(inc.get("reporting_deadline"), inc["status"]), unsafe_allow_html=True)

            # Absence tracking for over-7-day cases
            if inc["incident_type"] == "over_7_day" and inc.get("absence_days") is not None:
                if inc["absence_days"] > 7:
                    st.warning(f"📅 Absence: **{inc['absence_days']} days** — exceeds 7-day RIDDOR threshold")
                else:
                    st.info(f"📅 Absence: **{inc['absence_days']} days** — monitoring (7-day threshold not yet reached)")

            # Expandable detail
            with st.expander("View Details"):
                st.markdown(f"**Description:** {inc['description']}")
                if inc.get("injury_details"):
                    st.markdown(f"**Injury:** {inc['injury_details']}")
                if inc.get("ai_reasoning"):
                    st.markdown(f"**AI Assessment:** {inc['ai_reasoning']}")

                # Actions for this incident
                actions = [a for a in st.session_state.actions if a["incident_id"] == inc["id"]]
                if actions:
                    st.markdown("**Timeline:**")
                    for a in actions:
                        st.caption(f"🔹 {a['timestamp'][:10]} — {a['description']} ({a['performed_by']})")

                # Status update buttons
                col_a, col_b, col_c = st.columns(3)
                if col_a.button("Mark as Submitted", key=f"submit_{inc['id']}"):
                    st.session_state.incidents[inc["id"]]["status"] = "submitted"
                    st.session_state.incidents[inc["id"]]["submitted_at"] = date.today().isoformat()
                    st.rerun()
                if col_b.button("Mark as Investigating", key=f"invest_{inc['id']}"):
                    st.session_state.incidents[inc["id"]]["status"] = "investigating"
                    st.rerun()
                if col_c.button("Close Case", key=f"close_{inc['id']}"):
                    st.session_state.incidents[inc["id"]]["status"] = "closed"
                    st.rerun()
