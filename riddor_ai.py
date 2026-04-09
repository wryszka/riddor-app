"""AI integration using Databricks Foundation Model serving."""

import json
import os
from databricks.sdk import WorkspaceClient
from openai import OpenAI

_client = None
_model = None


def _get_model() -> str:
    """Get model name from AI_ENDPOINT_NAME env var."""
    global _model
    if _model is None:
        _model = os.environ.get("AI_ENDPOINT_NAME", "databricks-claude-sonnet-4-6")
    return _model


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        w = WorkspaceClient()
        _client = OpenAI(
            api_key=w.config.oauth_token().access_token,
            base_url=f"{w.config.host}/serving-endpoints",
        )
    return _client


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

## Style
- Be specific, cite RIDDOR categories
- Plain English for H&S managers
- If uncertain, err on side of reporting
- Flag borderline cases
- Use plain text, not markdown formatting"""

CLASSIFICATION_PROMPT = """You are a RIDDOR incident classification engine. Analyse the incident and return ONLY valid JSON:

{
  "is_reportable": true/false,
  "category": "death|specified_injury|over_7_day|non_worker_hospital|occupational_disease|dangerous_occurrence|not_reportable",
  "category_label": "Human-readable name",
  "confidence": "high|medium|low",
  "reporting_deadline": "Deadline description",
  "reporting_method": "How to report",
  "reasoning": "2-3 sentence explanation",
  "key_factors": ["factor1", "factor2"],
  "actions_required": ["action1", "action2"],
  "records_to_keep": ["record1", "record2"]
}

Rules:
1. Deaths → "death"
2. Specified injuries to WORKERS (fractures excl. fingers/thumbs/toes, amputations, crush to head/torso, burns >10%, loss of sight/consciousness, scalping, hypothermia) → "specified_injury"
3. Worker absent 7+ consecutive days after accident → "over_7_day"
4. Non-worker taken DIRECTLY from scene to hospital for treatment → "non_worker_hospital"
5. Doctor-diagnosed occupational disease → "occupational_disease"
6. Dangerous occurrences (Schedule 2) → "dangerous_occurrence"
7. Everything else → "not_reportable"

Return ONLY the JSON object, no other text."""


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
