"""RIDDOR reference data, mock incidents, and classification configs.

Mock data uses a fixed reference date (REFERENCE_DATE) for all incidents,
then `_relative()` rewrites them to be relative to today at module load time.
This way the demo always shows a realistic mix of overdue/current cases
no matter when it's run.
"""

from datetime import date, datetime, timedelta

# All incident dates below are written as if today were 2026-04-01.
# At module load time, we shift every date so the same offsets apply to
# the actual current date.
REFERENCE_DATE = date(2026, 4, 1)

# ── Colour & label configs ────────────────────────────────────────────

INCIDENT_TYPE_CONFIG = {
    "death": {"label": "Death", "color": "#111827", "emoji": "💀"},
    "specified_injury": {"label": "Specified Injury", "color": "#dc2626", "emoji": "🦴"},
    "over_7_day": {"label": "Over 7-Day", "color": "#ea580c", "emoji": "📅"},
    "non_worker_hospital": {"label": "Non-Worker Hospital", "color": "#7c3aed", "emoji": "🏥"},
    "occupational_disease": {"label": "Occupational Disease", "color": "#2563eb", "emoji": "🫁"},
    "dangerous_occurrence": {"label": "Dangerous Occurrence", "color": "#d97706", "emoji": "⚠️"},
    "not_reportable": {"label": "Not Reportable", "color": "#6b7280", "emoji": "✅"},
}

STATUS_CONFIG = {
    "open": {"label": "Open", "color": "#2563eb"},
    "investigating": {"label": "Investigating", "color": "#d97706"},
    "pending_report": {"label": "Pending Report", "color": "#ea580c"},
    "submitted": {"label": "Submitted to HSE", "color": "#16a34a"},
    "closed": {"label": "Closed", "color": "#6b7280"},
}


def get_days_remaining(deadline_str: str | None) -> int | None:
    if not deadline_str:
        return None
    try:
        dl = datetime.strptime(deadline_str, "%Y-%m-%d").date()
        return (dl - date.today()).days
    except (ValueError, TypeError):
        return None


# ── Date-shifting so demo always looks fresh ─────────────────────────

_SHIFT_DAYS = (date.today() - REFERENCE_DATE).days


def _shift_date(s: str | None) -> str | None:
    """Shift a YYYY-MM-DD or ISO datetime string by _SHIFT_DAYS."""
    if not s:
        return s
    try:
        if "T" in s:
            dt = datetime.fromisoformat(s)
            return (dt + timedelta(days=_SHIFT_DAYS)).isoformat()
        d = datetime.strptime(s, "%Y-%m-%d").date()
        return (d + timedelta(days=_SHIFT_DAYS)).strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return s


def _shift_incidents(incidents: list[dict]) -> list[dict]:
    date_fields = ("incident_date", "created_at", "reporting_deadline", "submitted_at")
    out = []
    for inc in incidents:
        new = dict(inc)
        for f in date_fields:
            if new.get(f):
                new[f] = _shift_date(new[f])
        # Update reference number to reflect new date
        if new.get("incident_date"):
            d = new["incident_date"][:10].replace("-", "")
            ref_suffix = new["reference"].split("-")[-1]
            new["reference"] = f"RIDDOR-{d}-{ref_suffix}"
        out.append(new)
    return out


def _shift_actions(actions: list[dict]) -> list[dict]:
    out = []
    for a in actions:
        new = dict(a)
        if new.get("timestamp"):
            new["timestamp"] = _shift_date(new["timestamp"])
        out.append(new)
    return out


# ── Mock data (raw — dates relative to REFERENCE_DATE) ───────────────

_RAW_INCIDENTS = [
    {
        "id": "inc-001",
        "reference": "RIDDOR-20260322-A1B2",
        "created_at": "2026-03-22T09:30:00",
        "incident_date": "2026-03-22",
        "incident_type": "specified_injury",
        "person_name": "James Whitfield",
        "person_type": "worker",
        "department": "Manufacturing",
        "location": "Assembly Line B, Building 3",
        "description": "Employee slipped on oil residue near CNC machine and fell heavily. Sustained a fracture to the left radius (forearm). Taken to A&E by ambulance.",
        "injury_details": "Closed fracture to left radius. Cast applied at Royal Infirmary.",
        "ai_classification": {
            "is_reportable": True,
            "category": "specified_injury",
            "category_label": "Specified Injury",
            "confidence": "high",
            "reasoning": "A fracture to the forearm (radius) is a specified injury under RIDDOR as it is a fracture other than to fingers, thumbs, or toes. The injured person is a worker and the incident occurred in the workplace.",
            "reporting_deadline": "Without delay (written confirmation within 10 days)",
            "reporting_method": "Phone HSE on 0345 300 9923 or report online at www.hse.gov.uk/riddor",
            "key_factors": ["Worker", "Fracture to radius (forearm)", "Workplace slip"],
            "actions_required": ["Report to HSE without delay", "Investigate oil residue source", "Review cleaning procedures for Assembly Line B"],
            "records_to_keep": ["Accident book entry", "RIDDOR report copy", "Investigation findings"],
        },
        "ai_reasoning": "A fracture to the forearm (radius) is a specified injury under RIDDOR as it is a fracture other than to fingers, thumbs, or toes.",
        "manager_override": None,
        "status": "open",
        "reporting_deadline": "2026-03-27",
        "hse_reference": None,
        "submitted_at": None,
        "reporter_name": "Sarah Mitchell",
        "absence_days": 9,
    },
    {
        "id": "inc-002",
        "reference": "RIDDOR-20260305-C3D4",
        "created_at": "2026-03-05T14:15:00",
        "incident_date": "2026-03-05",
        "incident_type": "over_7_day",
        "person_name": "Priya Sharma",
        "person_type": "worker",
        "department": "Warehouse",
        "location": "Goods Inward Bay, Warehouse 2",
        "description": "Employee was struck by a pallet that fell from a forklift. Sustained back injury and severe bruising. Has been absent from work since the accident.",
        "injury_details": "Lumbar strain and extensive bruising to back and shoulders. GP signed off for 3 weeks.",
        "ai_classification": {
            "is_reportable": True,
            "category": "over_7_day",
            "category_label": "Over-7-Day Incapacitation",
            "confidence": "high",
            "reasoning": "The worker has been absent for more than 7 consecutive days following the accident (not counting the day of the accident). This meets the over-7-day incapacitation threshold.",
            "reporting_deadline": "Within 15 days of the accident (by 2026-03-20)",
            "reporting_method": "Report online at www.hse.gov.uk/riddor",
            "key_factors": ["Worker", "Absence exceeding 7 days", "Unable to perform normal duties"],
            "actions_required": ["Report to HSE within 15 days", "Review forklift operating procedures", "Investigate pallet securing methods"],
            "records_to_keep": ["Accident book entry", "RIDDOR report copy", "GP fit notes", "Absence records"],
        },
        "ai_reasoning": "The worker has been absent for more than 7 consecutive days following the accident.",
        "manager_override": None,
        "status": "pending_report",
        "reporting_deadline": "2026-03-20",
        "hse_reference": None,
        "submitted_at": None,
        "reporter_name": "David Chen",
        "absence_days": 27,
    },
    {
        "id": "inc-003",
        "reference": "RIDDOR-20260305-E5F6",
        "created_at": "2026-03-05T11:00:00",
        "incident_date": "2026-03-05",
        "incident_type": "dangerous_occurrence",
        "person_name": "N/A",
        "person_type": "worker",
        "department": "Maintenance",
        "location": "Boiler Room, Main Building",
        "description": "Pressure relief valve on the main boiler failed, resulting in an uncontrolled release of steam into the boiler room. No injuries but the area was evacuated immediately.",
        "injury_details": "No injuries sustained.",
        "ai_classification": {
            "is_reportable": True,
            "category": "dangerous_occurrence",
            "category_label": "Dangerous Occurrence",
            "confidence": "high",
            "reasoning": "An uncontrolled release of steam from a pressure vessel is a dangerous occurrence under Schedule 2 of RIDDOR 2013.",
            "reporting_deadline": "Without delay",
            "reporting_method": "Report online at www.hse.gov.uk/riddor",
            "key_factors": ["Pressure vessel failure", "Uncontrolled steam release", "Potential for serious injury"],
            "actions_required": ["Report to HSE without delay", "Isolate boiler system", "Commission independent inspection"],
            "records_to_keep": ["RIDDOR report copy", "Maintenance records", "Inspection reports"],
        },
        "ai_reasoning": "An uncontrolled release of steam from a pressure vessel is a dangerous occurrence under Schedule 2 of RIDDOR 2013.",
        "manager_override": None,
        "status": "submitted",
        "reporting_deadline": "2026-03-05",
        "hse_reference": "HSE-2026-88421",
        "submitted_at": "2026-03-05T15:30:00",
        "reporter_name": "Mark Thompson",
        "absence_days": None,
    },
    {
        "id": "inc-004",
        "reference": "RIDDOR-20260301-G7H8",
        "created_at": "2026-03-01T16:45:00",
        "incident_date": "2026-03-01",
        "incident_type": "non_worker_hospital",
        "person_name": "Margaret Evans",
        "person_type": "non_worker",
        "department": "Reception",
        "location": "Main Reception Area",
        "description": "Visitor tripped over a loose carpet tile in the reception area and fell, hitting her head on the reception desk. Paramedics took her directly to hospital from the scene for treatment of a head laceration.",
        "injury_details": "Head laceration requiring 6 stitches. Observed for concussion.",
        "ai_classification": {
            "is_reportable": True,
            "category": "non_worker_hospital",
            "category_label": "Non-Worker Taken to Hospital",
            "confidence": "high",
            "reasoning": "The injured person is a non-worker (visitor) who was taken directly from the scene of the accident to hospital for treatment.",
            "reporting_deadline": "Without delay (written confirmation within 10 days)",
            "reporting_method": "Report online at www.hse.gov.uk/riddor",
            "key_factors": ["Non-worker (visitor)", "Taken directly from scene to hospital", "Treatment required"],
            "actions_required": ["Report to HSE without delay", "Fix carpet tile immediately", "Inspect all floor coverings"],
            "records_to_keep": ["Accident book entry", "RIDDOR report copy", "Photos of carpet tile"],
        },
        "ai_reasoning": "Non-worker taken directly from scene to hospital for treatment.",
        "manager_override": None,
        "status": "submitted",
        "reporting_deadline": "2026-03-11",
        "hse_reference": "HSE-2026-87654",
        "submitted_at": "2026-03-01T18:00:00",
        "reporter_name": "Sarah Mitchell",
        "absence_days": None,
    },
    {
        "id": "inc-005",
        "reference": "RIDDOR-20260220-I9J0",
        "created_at": "2026-02-20T10:00:00",
        "incident_date": "2026-02-20",
        "incident_type": "occupational_disease",
        "person_name": "Robert Clarke",
        "person_type": "worker",
        "department": "Paint Shop",
        "location": "Spray Booth 1",
        "description": "Employee diagnosed with occupational asthma by occupational health physician. Has been working in the paint shop for 8 years with exposure to isocyanate paints.",
        "injury_details": "Occupational asthma diagnosis confirmed by Dr. Williams.",
        "ai_classification": {
            "is_reportable": True,
            "category": "occupational_disease",
            "category_label": "Occupational Disease",
            "confidence": "high",
            "reasoning": "Occupational asthma diagnosed by a doctor and linked to workplace exposure to isocyanates is a reportable occupational disease under RIDDOR 2013.",
            "reporting_deadline": "Without delay",
            "reporting_method": "Report online at www.hse.gov.uk/riddor",
            "key_factors": ["Doctor-diagnosed occupational asthma", "Workplace exposure to isocyanates"],
            "actions_required": ["Report to HSE without delay", "Review COSHH assessments", "Health surveillance for all paint shop workers"],
            "records_to_keep": ["RIDDOR report copy", "Occupational health report", "COSHH assessments"],
        },
        "ai_reasoning": "Occupational asthma diagnosed by a doctor linked to workplace exposure is reportable under RIDDOR.",
        "manager_override": None,
        "status": "submitted",
        "reporting_deadline": "2026-02-20",
        "hse_reference": "HSE-2026-82100",
        "submitted_at": "2026-02-20T16:00:00",
        "reporter_name": "David Chen",
        "absence_days": None,
    },
    {
        "id": "inc-006",
        "reference": "RIDDOR-20260318-K1L2",
        "created_at": "2026-03-18T08:30:00",
        "incident_date": "2026-03-18",
        "incident_type": "not_reportable",
        "person_name": "Tom Bradley",
        "person_type": "worker",
        "department": "Office - IT",
        "location": "Office Floor 2",
        "description": "Employee cut his index finger on a sharp edge of a server rack while installing new equipment. First aid applied on site.",
        "injury_details": "Minor laceration to right index finger. Cleaned and dressed by first aider.",
        "ai_classification": {
            "is_reportable": False,
            "category": "not_reportable",
            "category_label": "Not Reportable Under RIDDOR",
            "confidence": "high",
            "reasoning": "A minor cut to a finger requiring only first aid is not reportable under RIDDOR.",
            "reporting_deadline": "N/A",
            "reporting_method": "N/A - record in accident book only",
            "key_factors": ["Minor injury", "First aid only", "No expected absence"],
            "actions_required": ["Record in accident book", "Check server rack edges"],
            "records_to_keep": ["Accident book entry"],
        },
        "ai_reasoning": "A minor cut to a finger requiring only first aid is not reportable under RIDDOR.",
        "manager_override": None,
        "status": "closed",
        "reporting_deadline": None,
        "hse_reference": None,
        "submitted_at": None,
        "reporter_name": "Sarah Mitchell",
        "absence_days": 0,
    },
    {
        "id": "inc-007",
        "reference": "RIDDOR-20260324-M3N4",
        "created_at": "2026-03-24T13:00:00",
        "incident_date": "2026-03-24",
        "incident_type": "specified_injury",
        "person_name": "Angela Foster",
        "person_type": "worker",
        "department": "Kitchen",
        "location": "Staff Canteen Kitchen",
        "description": "Kitchen worker suffered severe burns to both forearms when a large pan of boiling water was knocked from the stove. Burns cover approximately 12% of body surface area.",
        "injury_details": "Second and third degree burns to both forearms, estimated 12% body surface area. Admitted to Burns Unit.",
        "ai_classification": {
            "is_reportable": True,
            "category": "specified_injury",
            "category_label": "Specified Injury",
            "confidence": "high",
            "reasoning": "Burns covering more than 10% of the body are a specified injury under RIDDOR.",
            "reporting_deadline": "Without delay (written confirmation within 10 days)",
            "reporting_method": "Phone HSE on 0345 300 9923 or report online",
            "key_factors": ["Worker", "Burns >10% body surface area", "Hospital admission"],
            "actions_required": ["Report to HSE without delay via phone", "Investigate kitchen safety", "Review handling of hot liquids"],
            "records_to_keep": ["Accident book entry", "RIDDOR report copy", "Hospital records", "Investigation report"],
        },
        "ai_reasoning": "Burns covering more than 10% of the body are a specified injury under RIDDOR.",
        "manager_override": None,
        "status": "investigating",
        "reporting_deadline": "2026-04-03",
        "hse_reference": None,
        "submitted_at": None,
        "reporter_name": "Mark Thompson",
        "absence_days": 7,
    },
    {
        "id": "inc-008",
        "reference": "RIDDOR-20260120-O5P6",
        "created_at": "2026-01-20T09:00:00",
        "incident_date": "2026-01-20",
        "incident_type": "death",
        "person_name": "William Porter",
        "person_type": "worker",
        "department": "Construction",
        "location": "Building Site - Sector 4, Roof Level",
        "description": "Worker fell from scaffolding at approximately 8 metres height. Despite immediate first aid and emergency services attendance, the worker was pronounced dead at the scene.",
        "injury_details": "Fatal injuries from fall at height.",
        "ai_classification": {
            "is_reportable": True,
            "category": "death",
            "category_label": "Death",
            "confidence": "high",
            "reasoning": "Any death arising from a work-related accident must be reported under RIDDOR immediately.",
            "reporting_deadline": "Without delay - immediate notification required",
            "reporting_method": "Phone HSE on 0345 300 9923 immediately",
            "key_factors": ["Fatality", "Fall from height", "Failure of fall protection"],
            "actions_required": ["Notify HSE immediately by phone", "Preserve the scene", "Notify next of kin", "Full investigation"],
            "records_to_keep": ["RIDDOR report copy", "Scene photographs", "Witness statements", "Equipment records"],
        },
        "ai_reasoning": "Any death arising from a work-related accident must be reported under RIDDOR immediately.",
        "manager_override": None,
        "status": "submitted",
        "reporting_deadline": "2026-01-20",
        "hse_reference": "HSE-2026-71002",
        "submitted_at": "2026-01-20T09:45:00",
        "reporter_name": "David Chen",
        "absence_days": None,
    },
    {
        "id": "inc-009",
        "reference": "RIDDOR-20260318-Q7R8",
        "created_at": "2026-03-18T10:30:00",
        "incident_date": "2026-03-18",
        "incident_type": "over_7_day",
        "person_name": "Lisa Nguyen",
        "person_type": "worker",
        "department": "Warehouse",
        "location": "Loading Dock 3",
        "description": "Employee twisted her ankle stepping off the loading dock edge. X-ray confirmed no fracture but severe ligament damage. GP has signed her off for 2 weeks.",
        "injury_details": "Severe ankle sprain with ligament damage. No fracture. Signed off for 14 days.",
        "ai_classification": {
            "is_reportable": True,
            "category": "over_7_day",
            "category_label": "Over-7-Day Incapacitation",
            "confidence": "high",
            "reasoning": "The worker will be absent for 14 days which exceeds the 7-day threshold.",
            "reporting_deadline": "Within 15 days of the accident (by 2026-04-02)",
            "reporting_method": "Report online at www.hse.gov.uk/riddor",
            "key_factors": ["Worker", "Expected absence of 14 days", "Exceeds 7-day threshold"],
            "actions_required": ["Monitor absence - report once 7 days confirmed", "Review loading dock edge markings"],
            "records_to_keep": ["Accident book entry", "RIDDOR report copy", "GP fit notes"],
        },
        "ai_reasoning": "Worker will be absent for 14 days, exceeding the 7-day incapacitation threshold.",
        "manager_override": None,
        "status": "open",
        "reporting_deadline": "2026-04-02",
        "hse_reference": None,
        "submitted_at": None,
        "reporter_name": "Sarah Mitchell",
        "absence_days": 13,
    },
    {
        "id": "inc-010",
        "reference": "RIDDOR-20260212-S9T0",
        "created_at": "2026-02-12T15:00:00",
        "incident_date": "2026-02-12",
        "incident_type": "non_worker_hospital",
        "person_name": "George Patel",
        "person_type": "non_worker",
        "department": "Retail Floor",
        "location": "Aisle 5, Ground Floor Shop",
        "description": "Customer slipped on a wet floor (recently mopped, warning sign had blown over). Fell and sustained a suspected fractured hip. Ambulance called and customer taken directly to hospital.",
        "injury_details": "Suspected fractured hip. Taken to A&E by ambulance from scene.",
        "ai_classification": {
            "is_reportable": True,
            "category": "non_worker_hospital",
            "category_label": "Non-Worker Taken to Hospital",
            "confidence": "high",
            "reasoning": "A non-worker taken directly from the scene to hospital for treatment is reportable.",
            "reporting_deadline": "Without delay (written confirmation within 10 days)",
            "reporting_method": "Report online at www.hse.gov.uk/riddor",
            "key_factors": ["Non-worker (customer)", "Taken directly from scene to hospital"],
            "actions_required": ["Report to HSE without delay", "Review wet floor procedures", "Secure warning signs"],
            "records_to_keep": ["Accident book entry", "RIDDOR report copy", "CCTV footage"],
        },
        "ai_reasoning": "Non-worker taken directly from the scene to hospital for treatment.",
        "manager_override": None,
        "status": "submitted",
        "reporting_deadline": "2026-02-22",
        "hse_reference": "HSE-2026-78900",
        "submitted_at": "2026-02-12T17:30:00",
        "reporter_name": "Mark Thompson",
        "absence_days": None,
    },
]

_RAW_ACTIONS = [
    {"id": "act-001", "incident_id": "inc-001", "action_type": "created", "description": "Incident report filed", "performed_by": "Sarah Mitchell", "timestamp": "2026-03-22T09:30:00"},
    {"id": "act-002", "incident_id": "inc-001", "action_type": "classified", "description": "AI classified as Specified Injury (fracture)", "performed_by": "System", "timestamp": "2026-03-22T09:31:00"},
    {"id": "act-003", "incident_id": "inc-001", "action_type": "note", "description": "Investigation ongoing — reviewing CCTV footage of slip", "performed_by": "David Chen", "timestamp": "2026-03-23T10:00:00"},
    {"id": "act-004", "incident_id": "inc-002", "action_type": "created", "description": "Incident report filed", "performed_by": "David Chen", "timestamp": "2026-03-05T14:15:00"},
    {"id": "act-005", "incident_id": "inc-002", "action_type": "classified", "description": "AI classified as Over-7-Day Incapacitation", "performed_by": "System", "timestamp": "2026-03-05T14:16:00"},
    {"id": "act-006", "incident_id": "inc-002", "action_type": "absence_update", "description": "Absence day count: 27 days. RIDDOR threshold exceeded — report overdue.", "performed_by": "System", "timestamp": "2026-03-30T08:00:00"},
    {"id": "act-007", "incident_id": "inc-003", "action_type": "created", "description": "Dangerous occurrence reported", "performed_by": "Mark Thompson", "timestamp": "2026-03-05T11:00:00"},
    {"id": "act-008", "incident_id": "inc-003", "action_type": "submitted", "description": "RIDDOR report submitted to HSE. Ref: HSE-2026-88421", "performed_by": "Sarah Mitchell", "timestamp": "2026-03-05T15:30:00"},
    {"id": "act-009", "incident_id": "inc-004", "action_type": "created", "description": "Visitor incident report filed", "performed_by": "Sarah Mitchell", "timestamp": "2026-03-01T16:45:00"},
    {"id": "act-010", "incident_id": "inc-004", "action_type": "submitted", "description": "RIDDOR report submitted to HSE. Ref: HSE-2026-87654", "performed_by": "Sarah Mitchell", "timestamp": "2026-03-01T18:00:00"},
    {"id": "act-011", "incident_id": "inc-008", "action_type": "created", "description": "Fatal incident report filed", "performed_by": "David Chen", "timestamp": "2026-01-20T09:00:00"},
    {"id": "act-012", "incident_id": "inc-008", "action_type": "submitted", "description": "RIDDOR report submitted to HSE by phone. Ref: HSE-2026-71002", "performed_by": "David Chen", "timestamp": "2026-01-20T09:45:00"},
    {"id": "act-013", "incident_id": "inc-008", "action_type": "note", "description": "HSE inspector visit scheduled", "performed_by": "Mark Thompson", "timestamp": "2026-01-20T14:00:00"},
]


# ── Public exports — dates shifted to be relative to today ───────────

MOCK_INCIDENTS = _shift_incidents(_RAW_INCIDENTS)
MOCK_ACTIONS = _shift_actions(_RAW_ACTIONS)
