"""AI Risk Assessment generation from a method statement.

Takes a method statement and produces a structured risk assessment in the
company format: one row per foreseeable hazard, with pre-/post-control risk
ratings and practical control measures.

Design note — the LLM proposes Likelihood and Consequence (1-5) for each
hazard. The arithmetic (L x C) and the result banding (LOW/MEDIUM/HIGH/VERY
HIGH) are computed HERE in Python, never by the model. This guarantees the
maths is always correct and makes scoring consistent across runs (Rule 4).
"""

import json


# ── Risk matrix (single source of truth) ─────────────────────────────

LIKELIHOOD_SCALE = {
    1: "Rare",
    2: "Unlikely",
    3: "Possible",
    4: "Likely",
    5: "Almost Certain",
}
CONSEQUENCE_SCALE = {
    1: "Minor Injury",
    2: "First Aid Injury",
    3: "Lost Time Injury",
    4: "Major Injury",
    5: "Fatality",
}


def _clamp(v, lo=1, hi=5) -> int:
    try:
        v = int(round(float(v)))
    except (TypeError, ValueError):
        v = lo
    return max(lo, min(hi, v))


def risk_category(rating: int) -> str:
    """Convert a 1-25 risk rating into the company result band."""
    if rating <= 4:
        return "LOW"
    if rating <= 9:
        return "MEDIUM"
    if rating <= 15:
        return "HIGH"
    return "VERY HIGH"


# ── System prompt — behave like an experienced H&S Advisor ───────────

RA_GENERATION_PROMPT = """You are an experienced UK Health & Safety Advisor (CMIOSH-level) writing a formal risk assessment from a method statement. You think like an assessor reviewing work on site, not a text extractor.

## Your job
Read the method statement, understand the WORK being carried out, and produce a complete risk assessment. You must reason through these steps internally and return the result as JSON.

### Step 1 - Identify activities
Break the work into individual activities (e.g. "Prepare chemical solution", "Transport equipment", "Mop floor", "Dispose of waste").

### Step 2 - Identify foreseeable hazards (CRITICAL)
For each activity, identify the foreseeable hazards a competent assessor would expect - EVEN IF THEY ARE NOT MENTIONED in the method statement. Use your industry knowledge.
Example: "Move boxes from vehicle to storeroom" must surface manual handling, vehicle movements, slips and trips, crush injuries and falling objects, even though none are written down.

### Step 3 - Potential harm
For each hazard, list the likely harm (e.g. COSHH -> skin/eye irritation, inhalation, ingestion, chemical burns; Manual handling -> musculoskeletal/back injury, strains; Slips/trips -> cuts, bruises, fractures, head injuries).

### Step 4 - Pre-control scoring
Score the risk BEFORE controls using the matrix below. Likelihood 1-5, Consequence 1-5.

### Step 5 - Control measures
Generate practical, SPECIFIC controls based on the activity, the hazard, industry good practice, applicable UK legislation and reasonable company standards. They must be realistic and actionable.
GOOD: "Wear EN388 cut-resistant gloves", "Establish exclusion zone around work area", "Use mechanical lifting aid where load exceeds safe lifting limits", "Decant chemical at low level to prevent splash-back".
BAD (never use): "Take care", "Follow procedure", "Be careful", "Use common sense".

### Step 6 - Post-control scoring
Score the RESIDUAL risk after the controls are applied. Controls typically reduce Likelihood substantially; Consequence usually stays similar unless the controls remove the hazard.

## Risk matrix
Likelihood: 1 Rare, 2 Unlikely, 3 Possible, 4 Likely, 5 Almost Certain.
Consequence: 1 Minor Injury, 2 First Aid Injury, 3 Lost Time Injury, 4 Major Injury, 5 Fatality.

## Hazard library (use as a reference for completeness and consistency - not a limit)
- COSHH / hazardous substances: skin & eye irritation, inhalation, ingestion, chemical burns. Controls: COSHH assessment available, SDS on site, PPE per assessment, good ventilation, manufacturer instructions followed, no mixing of incompatible chemicals, hand washing after use.
- Manual handling: musculoskeletal, back, strains/sprains. Controls: manual handling training, team lifting, mechanical aids, avoid twisting, safe lifting technique, break loads down.
- Slips, trips and falls: cuts, bruises, fractures, head injuries. Controls: good housekeeping, clean spillages immediately, suitable footwear, keep area clear, signage for wet floors.
- Work at height: falls, falling objects. Controls: suitable access equipment inspected, edge protection, exclusion zone, tools tethered.
- Vehicle / plant movement: impact, crush. Controls: segregate pedestrians and vehicles, banksman, exclusion zone, hi-vis.
- Electrical: shock, burns. Controls: PAT-tested equipment, RCD protection, isolate before work, trained competent persons.
- Biological (e.g. cleaning toilets): infection. Controls: PPE (gloves/apron), hand hygiene, colour-coded equipment, vaccination where appropriate.
- Sharps / needlestick: punctures, blood-borne infection. Controls: sharps containers, never recap, puncture-resistant gloves, reporting procedure.
- Lone working: delayed help. Controls: check-in procedure, lone-worker device, dynamic risk assessment.

## Rules
1. ONE HAZARD PER ROW. Generate a separate object for each distinct hazard. A single task (e.g. cleaning toilets) will typically yield several hazards (COSHH, manual handling, slips/trips, biological, sharps, lone working if applicable).
2. Identify foreseeable hazards even when not stated.
3. Controls must be specific and realistic - never generic filler.
4. Keep scoring consistent: the same hazard in similar circumstances should score similarly.

## Output - return ONLY valid JSON, no preamble, no markdown fences:
{
  "task_title": "Short title for the overall task",
  "activities": ["activity 1", "activity 2", ...],
  "hazards": [
    {
      "hazard": "Hazard title, e.g. 'Chemical Solutions under COSHH Regulations'",
      "activity": "Which activity this relates to",
      "potential_harm": ["harm 1", "harm 2", ...],
      "persons_at_risk": ["Operatives", "Public", ...],
      "pre_likelihood": 1-5,
      "pre_consequence": 1-5,
      "control_measures": ["specific control 1", "specific control 2", ...],
      "post_likelihood": 1-5,
      "post_consequence": 1-5
    }
  ]
}

Do not include risk ratings or result categories - those are calculated separately. Provide only the likelihood and consequence scores."""


def _finalise_row(h: dict) -> dict:
    """Compute ratings and result band from the model's L/C scores."""
    pre_l = _clamp(h.get("pre_likelihood"))
    pre_c = _clamp(h.get("pre_consequence"))
    post_l = _clamp(h.get("post_likelihood"))
    post_c = _clamp(h.get("post_consequence"))
    pre_rating = pre_l * pre_c
    post_rating = post_l * post_c
    # Residual risk should never read as higher than the inherent risk.
    if post_rating > pre_rating:
        post_l, post_c = pre_l, pre_c
        post_rating = pre_rating
    return {
        "hazard": (h.get("hazard") or "Unspecified hazard").strip(),
        "activity": (h.get("activity") or "").strip(),
        "potential_harm": [x for x in (h.get("potential_harm") or []) if x],
        "persons_at_risk": [x for x in (h.get("persons_at_risk") or []) if x] or ["Operatives"],
        "control_measures": [x for x in (h.get("control_measures") or []) if x],
        "pre_likelihood": pre_l,
        "pre_consequence": pre_c,
        "pre_rating": pre_rating,
        "post_likelihood": post_l,
        "post_consequence": post_c,
        "post_rating": post_rating,
        "result": risk_category(post_rating),
    }


def generate_risk_assessment(method_statement: str, scope: str = "", activity: str = "") -> dict:
    """Generate a structured risk assessment from a method statement.

    Returns a dict with task_title, activities, and a list of fully-scored
    hazard rows (one per hazard), plus the assessment metadata.
    """
    parts = []
    if scope.strip():
        parts.append(f"## Scope of works\n{scope.strip()}")
    if activity.strip():
        parts.append(f"## Activity description\n{activity.strip()}")
    parts.append(f"## Method statement\n{method_statement.strip()}")
    user = "\n\n".join(parts)

    from riddor_ai import _chat, _extract_json
    raw = _chat(RA_GENERATION_PROMPT, user, temperature=0.1, max_tokens=4000)
    try:
        data = json.loads(_extract_json(raw))
    except json.JSONDecodeError:
        return {
            "task_title": "Risk assessment",
            "activities": [],
            "hazards": [],
            "_raw_response": raw,
        }

    rows = [_finalise_row(h) for h in (data.get("hazards") or [])]
    return {
        "task_title": (data.get("task_title") or "Risk Assessment").strip(),
        "activities": [a for a in (data.get("activities") or []) if a],
        "scope": scope.strip(),
        "activity": activity.strip(),
        "method_statement": method_statement.strip(),
        "hazards": rows,
        "highest_pre": max((r["pre_rating"] for r in rows), default=0),
        "highest_post": max((r["post_rating"] for r in rows), default=0),
    }
