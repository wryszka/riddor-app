"""Generate a Condensed COSHH Assessment PDF from extracted SDS data."""

import io
from fpdf import FPDF


_REPLACEMENTS = {
    # Dashes / hyphens
    "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-",
    "―": "-", "−": "-",
    # Bullets
    "•": "-", "‣": "-", "◦": "-", "·": "-",
    # Quotes
    "‘": "'", "’": "'", "‚": ",", "‛": "'",
    "“": '"', "”": '"', "„": '"', "‟": '"',
    # Math/comparison
    "≤": "<=", "≥": ">=", "≠": "!=", "≈": "~",
    "×": "x", "÷": "/",
    # Misc symbols
    "°": " deg", "μ": "u", "µ": "u",
    "→": "->", "←": "<-", "↑": "^", "↓": "v",
    "…": "...",
    " ": " ",  # non-breaking space
    "®": "(R)", "©": "(c)", "™": "(TM)",
}


def _safe(text) -> str:
    """fpdf2 default font is Latin-1; replace common unicode chars and drop the rest."""
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    for old, new in _REPLACEMENTS.items():
        text = text.replace(old, new)
    # Anything still outside latin-1 becomes '?'
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _risk_color(rating: str) -> tuple[int, int, int]:
    r = (rating or "").upper()
    if "HIGH" in r:
        return (220, 38, 38)
    if "MED" in r:
        return (217, 119, 6)
    return (22, 163, 74)  # LOW or unknown -> green


class _PDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(15, 23, 42)
        self.cell(0, 10, "CONDENSED COSHH ASSESSMENT", ln=True, align="C")
        self.ln(2)
        # Divider line
        self.set_draw_color(37, 99, 235)
        self.set_line_width(0.6)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(
            0, 10,
            f"AI-generated COSHH assessment | Page {self.page_no()} | Verify against original SDS",
            align="C",
        )


def _label_value(pdf: _PDF, label: str, value, indent: float = 0):
    """Render: 'Label: Value' on one line if short, or label + multi-line value."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(15, 23, 42)
    pdf.set_x(15 + indent)
    pdf.cell(45, 6, _safe(label) + ":", ln=False)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(0, 6, _safe(value))
    pdf.ln(0.5)


def _section(pdf: _PDF, title: str, body):
    """Render a section heading followed by body text or list."""
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(37, 99, 235)
    pdf.cell(0, 6, _safe(title) + ":", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(40, 40, 40)
    if isinstance(body, list):
        for item in body:
            if not item:
                continue
            pdf.set_x(20)
            pdf.multi_cell(0, 6, "- " + _safe(item))
    elif isinstance(body, dict):
        for k, v in body.items():
            if not v:
                continue
            pdf.set_x(20)
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(35, 6, _safe(k) + ":", ln=False)
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 6, _safe(v))
    elif body:
        pdf.set_x(15)
        pdf.multi_cell(0, 6, _safe(body))


def build_coshh_pdf(structured: dict, source_filename: str | None = None) -> bytes:
    """Build a Condensed COSHH Assessment PDF from extracted SDS data."""
    pdf = _PDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    product = structured.get("product") or {}
    hazards = structured.get("hazards") or {}
    ppe = structured.get("ppe") or {}
    first_aid = structured.get("first_aid") or {}
    storage = structured.get("storage") or {}

    # Header info — simple key/value rows
    _label_value(pdf, "Product Name", product.get("name") or source_filename or "Unknown")
    _label_value(pdf, "Use of Product", structured.get("use_of_product"))
    _label_value(pdf, "Form", structured.get("form") or structured.get("appearance"))
    _label_value(pdf, "pH", structured.get("ph"))

    # Method of application
    _section(pdf, "Method of Application", structured.get("method_of_application"))

    # CLP hazard
    clp = structured.get("clp_hazard_summary")
    if not clp and hazards.get("h_statements"):
        clp = "; ".join(hazards["h_statements"][:3])
    _section(pdf, "CLP Hazard Information", clp)

    # Routes of entry
    routes = structured.get("routes_of_entry") or []
    if routes:
        _section(pdf, "Routes of Entry", ", ".join(routes))

    # PPE — flatten the dict to bullet list
    ppe_items = []
    for label, value in [
        ("Hands", ppe.get("hands")),
        ("Eyes", ppe.get("eyes")),
        ("Respiratory", ppe.get("respiratory")),
        ("Body", ppe.get("body")),
    ]:
        if value:
            ppe_items.append(f"{label}: {value}")
    _section(pdf, "Mandatory PPE", ppe_items if ppe_items else None)

    # First aid
    fa_dict = {}
    if first_aid.get("skin_contact"): fa_dict["Skin contact"] = first_aid["skin_contact"]
    if first_aid.get("eye_contact"): fa_dict["Eye contact"] = first_aid["eye_contact"]
    if first_aid.get("inhalation"): fa_dict["Inhalation"] = first_aid["inhalation"]
    if first_aid.get("ingestion"): fa_dict["Ingestion"] = first_aid["ingestion"]
    _section(pdf, "First Aid Measures", fa_dict if fa_dict else None)

    # Spillage
    _section(pdf, "Spillage Procedure", structured.get("spill_response"))

    # Handling and Storage
    storage_text_parts = []
    if storage.get("conditions"): storage_text_parts.append(storage["conditions"])
    if storage.get("container"): storage_text_parts.append(f"Container: {storage['container']}")
    if storage.get("incompatible_materials"): storage_text_parts.append(f"Keep away from: {storage['incompatible_materials']}")
    _section(pdf, "Handling and Storage", " ".join(storage_text_parts) if storage_text_parts else None)

    # General precautions
    _section(pdf, "General Precautions", structured.get("general_precautions"))

    # Disposal
    _section(pdf, "Disposal", structured.get("disposal"))

    # Risk Rating — bold + colored
    pdf.ln(4)
    rating = (structured.get("risk_rating") or "LOW").upper()
    r, g, b = _risk_color(rating)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(80, 8, "Risk Rating (after control measures):", ln=False)
    pdf.set_text_color(r, g, b)
    pdf.cell(0, 8, _safe(rating), ln=True)

    # Output bytes — fpdf2 returns bytearray, need bytes
    out = pdf.output()
    if isinstance(out, (bytes, bytearray)):
        return bytes(out)
    # Older API returns a string; encode latin-1
    return out.encode("latin-1")
