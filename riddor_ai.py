"""AI integration using Databricks Foundation Model serving."""

import json
import os
from datetime import datetime
from databricks.sdk import WorkspaceClient
from openai import OpenAI

_model = None
_workspace_client = None


def _get_model() -> str:
    """Get model name from AI_ENDPOINT_NAME env var."""
    global _model
    if _model is None:
        _model = os.environ.get("AI_ENDPOINT_NAME", "databricks-claude-sonnet-4-6")
    return _model


def _get_workspace_client() -> WorkspaceClient:
    global _workspace_client
    if _workspace_client is None:
        _workspace_client = WorkspaceClient()
    return _workspace_client


def _get_client() -> OpenAI:
    """Create a fresh OpenAI client with a current token each time."""
    w = _get_workspace_client()
    return OpenAI(
        api_key=w.config.oauth_token().access_token,
        base_url=f"{w.config.host}/serving-endpoints",
    )


def _extract_text(content) -> str:
    """Extract plain text from response content — handles both str and list formats.

    Some models (GPT) return content as a list of typed blocks, e.g.:
      [{"type": "text", "text": "..."}, {"type": "reasoning", ...}]
    Others (Claude) return a plain string.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif block.get("type") == "reasoning":
                    # Extract from summary sub-blocks
                    for s in block.get("summary", []):
                        if isinstance(s, dict):
                            parts.append(s.get("text", ""))
            elif hasattr(block, "text"):
                parts.append(block.text)
        return "\n".join(parts).strip()
    return str(content)


def _chat(system: str, user: str, temperature: float = 0.1, max_tokens: int = 2000) -> str:
    client = _get_client()
    resp = client.chat.completions.create(
        model=_get_model(),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return _extract_text(resp.choices[0].message.content)


def _extract_json(text: str) -> str:
    """Extract a JSON object from text that may contain reasoning preamble."""
    import re
    # Strip markdown code fences
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t[3:]
        if t.endswith("```"):
            t = t[:-3]
        t = t.strip()
    # If it's already valid JSON, return it
    if t.startswith("{"):
        return t
    # Find the first { ... } block (the JSON object) in the text
    match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', t, re.DOTALL)
    if match:
        return match.group(0)
    return t


# ── System Prompts ────────────────────────────────────────────────────

RIDDOR_CHAT_PROMPT = """You are a RIDDOR (Reporting of Injuries, Diseases and Dangerous Occurrences Regulations 2013) expert assistant for UK Health & Safety managers. You ONLY answer questions about RIDDOR, workplace health and safety regulations, and incident classification. If asked about anything unrelated, politely redirect to RIDDOR topics.

## Your Knowledge Base

### Reportable Categories
1. **Deaths** — Any death arising from a work-related accident
2. **Specified Injuries** (workers only): Fractures (not fingers/thumbs/toes), amputations, loss of sight, crush injuries to head/torso, burns >10% body, loss of consciousness from head injury/asphyxia, scalping, hypothermia/heat illness in enclosed spaces
3. **Over-7-day incapacitation** (workers only): Absent or unable to do normal duties for 7+ consecutive days after day of accident. Weekends count. Day of accident doesn't count.
4. **Non-worker taken to hospital**: Only if taken DIRECTLY from scene for treatment (not precautionary)
5. **Occupational diseases**: Doctor-diagnosed — asthma, dermatitis, carpal tunnel, cancers, HAVS, etc.
6. **Dangerous occurrences**: Scaffold collapse, pressure vessel failure, uncontrolled substance release, electrical incidents, etc. (27 categories in Schedule 2)

### Deadlines
- Deaths/specified injuries: WITHOUT DELAY, written confirmation within 10 days
- Over-7-day: Within 15 days of accident
- Diseases/dangerous occurrences: WITHOUT DELAY

### Reporting
- Online: www.hse.gov.uk/riddor (all types)
- Phone: 0345 300 9923 (fatalities & specified injuries only, Mon-Fri 8:30am-5pm)
- Records: Keep for at least 3 years
- All accidents go in accident book regardless of RIDDOR status

### CRITICAL: Work-Relatedness Test (apply this BEFORE classifying as reportable)

The KEY question for any injury: **Did the work activity, environment, equipment, or management failure contribute to this injury?**

If NO → NOT RIDDOR reportable (record in accident book only)

**Exclusions — these are NOT RIDDOR reportable** even if they happen on workplace premises:
- **Just transiting / walking** between locations (e.g. going to office, walking to another building, no equipment in hands) is NOT a work activity
- **Personal acts**: stopping to chat with a friend and tripping, clocking in and walking to staff room, going to get changed, accidents during breaks/lunch
- **Horseplay / play fighting / messing about** — running in corridors, larking around → personal act, not work
- **Normal body movements with no work hazard**: turning awkwardly while standing and pulling a muscle, tripping over your own feet
- **Pre-existing conditions** worsening during normal activity (e.g. knee injury worsens during normal walking)
- **Medical episodes** (heart attack, faint, seizure) unless caused by work
- **Commuting** to/from work
- **Non-work-related third party** acts (e.g. random assault unrelated to the work)
- **Accidents without clearly defined injury** are not reportable

**Examples that are NOT RIDDOR**:
- Employee runs in corridor messing around, trips and fractures wrist → horseplay, not work
- Worker stops to chat with colleague, trips on a step → personal act, not work activity
- Pulled muscle from turning awkwardly while standing → no work hazard, normal movement
- Worker faints due to underlying medical condition → medical episode, not work

**Examples that ARE RIDDOR-reportable** (work contributed):
- Slipped on wet floor that wasn't signposted → environmental/management failure
- Hand caught in machine guard that wasn't fitted → equipment/management failure
- Lifting injury exceeding manual handling assessment → work activity exceeded controls
- Fall from height with inadequate fall protection → equipment/management failure

When the description is ambiguous, ask: "Did work contribute in ANY way, even partially?" If yes → reportable. If clearly no → not reportable. Always explain your reasoning by referencing the work-relatedness test.

## Style
- Be specific, cite RIDDOR categories
- Plain English for H&S managers
- Apply the work-relatedness test rigorously
- Flag borderline cases and explain which exclusion may apply
- Use plain text, not markdown formatting"""

CLASSIFICATION_PROMPT = """You are a RIDDOR incident classification engine. Analyse the incident and return ONLY valid JSON.

## STEP 1: Apply the Work-Relatedness Test FIRST

The KEY question: **Did the work activity, environment, equipment, or management failure contribute to this injury?**

If NO → the incident is NOT RIDDOR-reportable regardless of injury severity. Classify as "not_reportable" and explain which exclusion applies in the reasoning.

### Exclusions — NOT RIDDOR even if they happen on workplace premises:
- **Just transiting / walking** between locations (going to office, walking to another building, no equipment) — not a work activity
- **Personal acts**: stopping to chat with a friend and tripping, clocking in and walking to staff room, going to get changed, accidents during breaks/lunch
- **Horseplay / play fighting / messing about** — running in corridors, larking around
- **Normal body movements with no work hazard**: turning awkwardly while standing and pulling a muscle, tripping over your own feet
- **Pre-existing conditions** worsening during normal activity (e.g. knee injury worsens during normal walking)
- **Medical episodes** (heart attack, faint, seizure) unless caused by work
- **Commuting** to/from work
- **Non-work-related third party** acts (e.g. random assault unrelated to work)
- **Accidents without clearly defined injury**

### Examples that are NOT RIDDOR (set is_reportable=false, category="not_reportable"):
- Employee runs in corridor messing around, trips and fractures wrist → horseplay
- Worker stops to chat, trips on a step → personal act
- Pulled muscle from turning awkwardly while standing → normal movement, no work hazard
- Worker faints due to underlying medical condition → medical episode

### Examples that ARE RIDDOR (work contributed):
- Slipped on wet floor that wasn't signposted → environmental/management failure
- Hand caught in unguarded machine → equipment/management failure
- Fall from height with inadequate fall protection → equipment failure
- Lifting injury exceeding manual handling assessment limits → work activity

## STEP 2: If work-related, classify the category

1. Death from work-related accident → "death"
2. Specified injuries to WORKERS (fractures excl. fingers/thumbs/toes, amputations, crush to head/torso, burns >10%, loss of sight/consciousness, scalping, hypothermia) → "specified_injury"
3. Worker absent 7+ consecutive days after accident → "over_7_day"
4. Non-worker taken DIRECTLY from scene to hospital for treatment → "non_worker_hospital"
5. Doctor-diagnosed occupational disease → "occupational_disease"
6. Dangerous occurrences (Schedule 2) → "dangerous_occurrence"
7. Everything else (work-related but doesn't meet thresholds) → "not_reportable"

## Output

Return ONLY this JSON, no other text:

{
  "is_reportable": true/false,
  "category": "death|specified_injury|over_7_day|non_worker_hospital|occupational_disease|dangerous_occurrence|not_reportable",
  "category_label": "Human-readable name",
  "confidence": "high|medium|low",
  "reporting_deadline": "Deadline description",
  "reporting_method": "How to report",
  "reasoning": "2-3 sentences. ALWAYS reference the work-relatedness test. If excluding, name the specific exclusion (horseplay, personal act, normal movement, etc.)",
  "key_factors": ["factor1", "factor2"],
  "actions_required": ["action1", "action2"],
  "records_to_keep": ["record1", "record2"]
}"""


# ── Public API ────────────────────────────────────────────────────────

def classify_incident(description: str) -> dict:
    """Classify an incident against RIDDOR categories."""
    raw = _chat(CLASSIFICATION_PROMPT, description)
    try:
        return json.loads(_extract_json(raw))
    except json.JSONDecodeError:
        return {
            "is_reportable": None,
            "category": "unknown",
            "category_label": "Unable to classify",
            "confidence": "low",
            "reasoning": raw,
            "reporting_deadline": "Please review manually",
            "reporting_method": "Contact HSE for guidance",
            "key_factors": [],
            "actions_required": ["Manual review required"],
            "records_to_keep": [],
        }


def chat_response(messages: list[dict]) -> str:
    """Get a chat response with full conversation history."""
    client = _get_client()
    full_messages = [{"role": "system", "content": RIDDOR_CHAT_PROMPT}] + messages[-12:]
    resp = client.chat.completions.create(
        model=_get_model(),
        messages=full_messages,
        temperature=0.3,
        max_tokens=1500,
    )
    return _extract_text(resp.choices[0].message.content)


# ── COSHH / Safety Data Sheet support ────────────────────────────────

SDS_EXTRACTION_PROMPT = """You are a COSHH (Control of Substances Hazardous to Health) document analysis engine. The user will provide the text of a Safety Data Sheet (SDS). Extract the key COSHH-relevant information and return ONLY valid JSON in this exact schema (use null when info is not in the document — do not guess):

{
  "product": {
    "name": "Product trade name",
    "code": "Product code if shown",
    "cas_number": "CAS number if shown",
    "ec_number": "EC number if shown"
  },
  "supplier": {
    "name": "Manufacturer/supplier name",
    "address": "Address",
    "phone": "Phone number",
    "emergency_phone": "Emergency contact"
  },
  "hazards": {
    "ghs_classifications": ["e.g. Skin Irrit. 2", "Eye Irrit. 2"],
    "pictograms": ["e.g. GHS07 (Exclamation Mark)", "GHS08 (Health Hazard)"],
    "signal_word": "Warning|Danger|null",
    "h_statements": ["H315: Causes skin irritation", "..."],
    "p_statements": ["P280: Wear protective gloves...", "..."]
  },
  "ppe": {
    "eyes": "Eye/face protection required",
    "hands": "Glove type and material",
    "respiratory": "Respiratory protection",
    "body": "Body/skin protection"
  },
  "first_aid": {
    "eye_contact": "Steps for eye contact",
    "skin_contact": "Steps for skin contact",
    "inhalation": "Steps for inhalation",
    "ingestion": "Steps for ingestion"
  },
  "fire_fighting": {
    "extinguishing_media": "Suitable extinguishers",
    "unsuitable_media": "Unsuitable extinguishers",
    "hazardous_combustion": "Hazardous combustion products"
  },
  "storage": {
    "conditions": "Storage conditions (temperature, ventilation)",
    "incompatible_materials": "Materials to keep away from",
    "container": "Container type/material"
  },
  "exposure_limits": {
    "wel_8h_twa": "8-hour Workplace Exposure Limit",
    "stel_15min": "15-minute Short-Term Exposure Limit",
    "biological_limits": "Biological limit values if any"
  },
  "spill_response": "Steps for accidental release / spillage",
  "disposal": "Disposal considerations",
  "physical_state": "Liquid|Solid|Gas|Aerosol",
  "appearance": "Colour and form description",
  "form": "Concise physical form description, e.g. 'Colourless liquid', 'White powder'",
  "ph": "pH value or range, e.g. '9-10 (mild alkaline)', null if not applicable",
  "use_of_product": "What the product is used for in 1-2 sentences",
  "method_of_application": "How the product is applied or used in workplace, including dilution rates and exposure scenarios. 2-4 sentences.",
  "clp_hazard_summary": "1-2 sentence plain-English summary of the CLP hazard classification (e.g. 'Irritant to eyes and skin')",
  "routes_of_entry": ["Skin contact", "Eye contact", "Inhalation", "Ingestion"],
  "general_precautions": "General handling precautions in 1-2 sentences",
  "risk_rating": "LOW|MEDIUM|HIGH — overall risk rating AFTER control measures (PPE + handling procedures) are applied. Most substances correctly handled with PPE are LOW. Use HIGH only for severely hazardous substances even with PPE.",
  "summary": "2-3 sentence plain-English summary of what this substance is and the key risks"
}

Return ONLY the JSON object — no preamble, no markdown fences, no explanation."""


COSHH_GENERAL_PROMPT = """You are a COSHH (Control of Substances Hazardous to Health Regulations 2002) expert assistant for UK Health & Safety managers.

You ONLY answer questions about:
- COSHH regulations and compliance
- Safety Data Sheets (SDS) — structure, sections, what to look for
- Chemical hazards, GHS classification, H/P statements
- Personal Protective Equipment (PPE) for chemical handling
- Workplace Exposure Limits (WEL, STEL)
- Storage, handling, spillage and disposal of hazardous substances
- First aid for chemical exposures (eye, skin, inhalation, ingestion)
- Risk assessments under COSHH

If asked about anything else (RIDDOR, employment law, general chemistry, unrelated topics), politely redirect:
"I can only help with COSHH and chemical safety questions. For RIDDOR incident classification, please use the RIDDOR section."

Style:
- Plain English for H&S managers, not chemistry jargon
- Be specific and practical — these answers may inform real workplace decisions
- If uncertain or the question requires substance-specific data, recommend uploading the SDS for that substance
- Use plain text formatting, minimal markdown"""


SDS_CHAT_SYSTEM_PROMPT = COSHH_GENERAL_PROMPT + """

## Document context

The user has uploaded a Safety Data Sheet. You have its full text and a structured extraction.

When answering about THIS specific substance:
- Answer ONLY from what's in the SDS. If the SDS doesn't say, say so explicitly — don't invent.
- Cite the SDS section where possible (e.g. "Section 4: First-aid measures").
- Don't make up CAS numbers, exposure limits, or chemical properties not stated.

For general COSHH questions not specific to this substance, you can use your general COSHH knowledge, but say so clearly."""


def extract_sds(text: str) -> dict:
    """Extract structured COSHH data from SDS text."""
    raw = _chat(SDS_EXTRACTION_PROMPT, text, max_tokens=3000)
    try:
        return json.loads(_extract_json(raw))
    except json.JSONDecodeError:
        return {
            "summary": "Failed to parse the document. The model returned text that was not valid JSON.",
            "_raw_response": raw,
        }


def sds_chat(messages: list[dict], document_text: str, structured: dict) -> str:
    """Answer a question about a specific SDS using its full text + structured extraction as context."""
    client = _get_client()
    # Truncate very long documents to fit context (keep first ~25k chars)
    doc_snippet = document_text[:25000]
    if len(document_text) > 25000:
        doc_snippet += "\n\n[... document truncated ...]"
    context = (
        f"## Structured extraction\n```json\n{json.dumps(structured, indent=2)}\n```\n\n"
        f"## Full document text\n{doc_snippet}"
    )
    full_messages = [
        {"role": "system", "content": SDS_CHAT_SYSTEM_PROMPT + "\n\n" + context},
    ] + messages[-10:]
    resp = client.chat.completions.create(
        model=_get_model(),
        messages=full_messages,
        temperature=0.2,
        max_tokens=1500,
    )
    return _extract_text(resp.choices[0].message.content)


def coshh_chat(messages: list[dict]) -> str:
    """General COSHH Q&A — no specific document context."""
    client = _get_client()
    full_messages = [{"role": "system", "content": COSHH_GENERAL_PROMPT}] + messages[-12:]
    resp = client.chat.completions.create(
        model=_get_model(),
        messages=full_messages,
        temperature=0.3,
        max_tokens=1500,
    )
    return _extract_text(resp.choices[0].message.content)


# ── Data Assistant — answers questions about app's actual data ───────

DATA_ASSISTANT_PROMPT = RIDDOR_CHAT_PROMPT + """

## You also have access to the organisation's actual data

You can answer questions about:
- The organisation's specific incidents (open, submitted, closed), their classifications, deadlines, and status
- COSHH chemicals on file (hazards, PPE, storage, exposure limits)
- Aggregate statistics, counts, and trends
- Overdue cases, urgent items, and patterns

When answering:
- For questions about specific cases, cite the reference number (e.g. RIDDOR-20260418-A1B2).
- For "how many" questions, give the exact count and list the items.
- For general RIDDOR rule questions (hypotheticals, "is X reportable?"), use your regulatory knowledge.
- For questions about the organisation's data, answer ONLY from the context below — never invent incidents, references, or chemical details that aren't there.
- If asked about specific data and the context doesn't have it, say so explicitly."""


def data_chat(messages: list[dict], incidents: list[dict], actions: list[dict], sds_documents: dict) -> str:
    """Answer a question grounded in the app's actual data (incidents + SDSs)."""
    client = _get_client()

    # Build compact incident summary (strip verbose fields to save tokens)
    incident_summary = []
    for inc in incidents:
        incident_summary.append({
            "ref": inc.get("reference"),
            "date": inc.get("incident_date"),
            "type": inc.get("incident_type"),
            "person": inc.get("person_name"),
            "person_type": inc.get("person_type"),
            "department": inc.get("department"),
            "location": inc.get("location"),
            "description": inc.get("description"),
            "status": inc.get("status"),
            "deadline": inc.get("reporting_deadline"),
            "submitted_at": inc.get("submitted_at"),
            "hse_reference": inc.get("hse_reference"),
            "absence_days": inc.get("absence_days"),
            "is_reportable": (inc.get("ai_classification") or {}).get("is_reportable"),
        })

    # Build SDS summary (just the structured extraction, not full text)
    sds_summary = {}
    for fname, doc in (sds_documents or {}).items():
        sds_summary[fname] = doc.get("structured", {})

    # Action timeline (last 30)
    action_summary = [
        {
            "incident": a.get("incident_id"),
            "type": a.get("action_type"),
            "description": a.get("description"),
            "by": a.get("performed_by"),
            "when": a.get("timestamp", "")[:10],
        }
        for a in (actions or [])[-30:]
    ]

    today = datetime.now().date().isoformat()

    context_parts = [f"## Today's date: {today}"]
    context_parts.append(f"\n## Incidents ({len(incident_summary)} total)\n```json\n{json.dumps(incident_summary, indent=2)}\n```")
    if action_summary:
        context_parts.append(f"\n## Recent activity\n```json\n{json.dumps(action_summary, indent=2)}\n```")
    if sds_summary:
        context_parts.append(f"\n## COSHH Safety Data Sheets on file ({len(sds_summary)} documents)\n```json\n{json.dumps(sds_summary, indent=2)}\n```")
    else:
        context_parts.append("\n## COSHH Safety Data Sheets on file\nNone uploaded yet.")

    full_context = "\n".join(context_parts)

    full_messages = [
        {"role": "system", "content": DATA_ASSISTANT_PROMPT + "\n\n" + full_context},
    ] + messages[-10:]
    resp = client.chat.completions.create(
        model=_get_model(),
        messages=full_messages,
        temperature=0.2,
        max_tokens=2000,
    )
    return _extract_text(resp.choices[0].message.content)
