"""Fill a docx template with extracted COSHH data using Jinja-style placeholders."""

from io import BytesIO


# Placeholders the user puts in their template, plus a description of what each holds.
# Order is the typical reading order of a COSHH form.
PLACEHOLDERS = [
    ("product_name", "Product trade name"),
    ("product_code", "Product code"),
    ("use_of_product", "What the product is used for"),
    ("form_and_colour", "Physical form and colour, e.g. 'Colourless liquid'"),
    ("method_of_application", "How the product is used, dilution rates"),
    ("clp_hazard_information", "CLP hazard summary + H-statements"),
    ("risk_rating", "LOW / MEDIUM / HIGH"),
    ("first_aid_skin", "Skin contact first aid"),
    ("first_aid_eye", "Eye contact first aid"),
    ("first_aid_ingestion", "Ingestion first aid"),
    ("first_aid_inhalation", "Inhalation first aid"),
    ("routes_of_entry", "Routes of entry (comma-separated)"),
    ("ppe_hands", "Hand protection"),
    ("ppe_eyes", "Eye protection"),
    ("ppe_respiratory", "Respiratory protection"),
    ("ppe_clothing", "Protective clothing"),
    ("ppe_footwear", "Protective footwear"),
    ("handling_and_storage", "Storage conditions and incompatibilities"),
    ("spillage_procedure", "Spill response"),
    ("general_precautions", "General handling precautions"),
    ("disposal", "Disposal considerations"),
    ("persons_at_risk", "Persons at risk (default: Employees)"),
    ("supplier_name", "Supplier / manufacturer name"),
]


def _join(items, sep=", "):
    if not items:
        return ""
    if isinstance(items, str):
        return items
    return sep.join(str(i) for i in items if i)


def build_context(structured: dict) -> dict:
    """Map extracted SDS fields to template placeholder values."""
    product = structured.get("product") or {}
    hazards = structured.get("hazards") or {}
    ppe = structured.get("ppe") or {}
    first_aid = structured.get("first_aid") or {}
    storage = structured.get("storage") or {}

    # CLP info — combine summary + H-statements
    clp = structured.get("clp_hazard_summary") or ""
    h_statements = hazards.get("h_statements") or []
    if h_statements:
        h_text = "\n".join(h_statements)
        clp = f"{clp}\n\n{h_text}".strip() if clp else h_text

    # Storage — combine conditions + container + incompatibilities
    storage_parts = []
    if storage.get("conditions"): storage_parts.append(storage["conditions"])
    if storage.get("container"): storage_parts.append(f"Container: {storage['container']}")
    if storage.get("incompatible_materials"): storage_parts.append(f"Keep away from: {storage['incompatible_materials']}")
    storage_text = " ".join(storage_parts)

    return {
        "product_name": product.get("name") or "",
        "product_code": product.get("code") or "",
        "supplier_name": (structured.get("supplier") or {}).get("name") or "",
        "use_of_product": structured.get("use_of_product") or "",
        "form_and_colour": structured.get("form") or structured.get("appearance") or "",
        "method_of_application": structured.get("method_of_application") or "",
        "clp_hazard_information": clp or "",
        "risk_rating": (structured.get("risk_rating") or "LOW").upper(),
        "first_aid_skin": first_aid.get("skin_contact") or "",
        "first_aid_eye": first_aid.get("eye_contact") or "",
        "first_aid_ingestion": first_aid.get("ingestion") or "",
        "first_aid_inhalation": first_aid.get("inhalation") or "",
        "routes_of_entry": _join(structured.get("routes_of_entry") or []),
        "ppe_hands": ppe.get("hands") or "",
        "ppe_eyes": ppe.get("eyes") or "",
        "ppe_respiratory": ppe.get("respiratory") or "",
        "ppe_clothing": ppe.get("body") or "",
        "ppe_footwear": "",
        "handling_and_storage": storage_text,
        "spillage_procedure": structured.get("spill_response") or "",
        "general_precautions": structured.get("general_precautions") or "",
        "disposal": structured.get("disposal") or "",
        "persons_at_risk": "Employees",
    }


def fill_template(template_bytes: bytes, structured: dict) -> bytes:
    """Render a docxtpl template with structured SDS data."""
    from docxtpl import DocxTemplate
    doc = DocxTemplate(BytesIO(template_bytes))
    context = build_context(structured)
    doc.render(context)
    out = BytesIO()
    doc.save(out)
    return out.getvalue()
