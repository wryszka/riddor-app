"""Fill a company SSRA (Site Specific Risk Assessment) .docx template.

The company template contains a "Risk Assessment" table whose data rows have
this 10-cell layout (some cells gridSpan-merged):

  [num] | Hazard + Potential harm | Pre L | Pre C | Pre Risk |
        | Control Measures | Post L | Post C | Post Risk | Result

We locate that table by its header row, use the first data row as a prototype,
and replace the example rows with the AI-generated hazards — preserving all
cell formatting, column spans, branding, headers/footers and the other form
sections exactly as they are in the customer's document.

Implemented with stdlib only (zipfile + ElementTree) so it has no dependency
on python-docx and behaves identically wherever it runs.
"""

import io
import zipfile
from copy import deepcopy
import xml.etree.ElementTree as ET

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
Wq = "{" + W + "}"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"

# Register the WordprocessingML namespace set so serialization keeps the
# conventional prefixes Word expects (avoids ns0: prefixes).
_NS = {
    "wpc": "http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
    "o": "urn:schemas-microsoft-com:office:office",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
    "v": "urn:schemas-microsoft-com:vml",
    "wp14": "http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "w10": "urn:schemas-microsoft-com:office:word",
    "w": W,
    "w14": "http://schemas.microsoft.com/office/word/2010/wordml",
    "w15": "http://schemas.microsoft.com/office/word/2012/wordml",
    "wpg": "http://schemas.microsoft.com/office/word/2010/wordprocessingGroup",
    "wpi": "http://schemas.microsoft.com/office/word/2010/wordprocessingInk",
    "wne": "http://schemas.microsoft.com/office/word/2006/wordml",
    "wps": "http://schemas.microsoft.com/office/word/2010/wordprocessingShape",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}
for _p, _u in _NS.items():
    ET.register_namespace(_p, _u)


def _cell_text(tc) -> str:
    return " ".join(
        "".join(t.text or "" for t in p.iter(Wq + "t")).strip()
        for p in tc.findall(Wq + "p")
    ).strip()


def _gridspan(tc) -> int:
    tcPr = tc.find(Wq + "tcPr")
    if tcPr is not None:
        gs = tcPr.find(Wq + "gridSpan")
        if gs is not None:
            try:
                return int(gs.get(Wq + "val"))
            except (TypeError, ValueError):
                return 1
    return 1


def _set_para_text(p, text: str):
    """Set a paragraph's text on its first run, preserving paragraph + run
    formatting; drop any additional runs/text."""
    runs = p.findall(Wq + "r")
    if not runs:
        r = ET.SubElement(p, Wq + "r")
        t = ET.SubElement(r, Wq + "t")
        t.set(XML_SPACE, "preserve")
        t.text = text
        return
    first = runs[0]
    for r in runs[1:]:
        p.remove(r)
    ts = first.findall(Wq + "t")
    # remove non-text run content that would inject stray glyphs (tabs/breaks)
    for br in first.findall(Wq + "br") + first.findall(Wq + "tab"):
        first.remove(br)
    if ts:
        for extra in ts[1:]:
            first.remove(extra)
        ts[0].text = text
        ts[0].set(XML_SPACE, "preserve")
    else:
        t = ET.SubElement(first, Wq + "t")
        t.set(XML_SPACE, "preserve")
        t.text = text


def _set_cell_lines(tc, lines):
    """Replace a cell's paragraphs with one paragraph per line, cloning the
    first paragraph so formatting is preserved."""
    paras = tc.findall(Wq + "p")
    proto = paras[0] if paras else None
    for p in paras:
        tc.remove(p)
    if not lines:
        lines = [""]
    for line in lines:
        newp = deepcopy(proto) if proto is not None else ET.SubElement(tc, Wq + "p")
        if proto is not None:
            _set_para_text(newp, line)
            tc.append(newp)
        else:
            _set_para_text(newp, line)


def _set_cell_text(tc, text: str):
    _set_cell_lines(tc, [text])


def _is_ra_header(tr) -> bool:
    """A row is the RA sub-header if it carries the column labels."""
    txt = " ".join(_cell_text(tc).lower() for tc in tr.findall(Wq + "tc"))
    return ("likelihood" in txt and "consequence" in txt
            and "risk rating" in txt and "control measures" in txt
            and "result" in txt)


def _find_ra_table_and_header(body):
    """Return (table_element, header_row_index) for the Risk Assessment table."""
    for tbl in body.iter(Wq + "tbl"):
        rows = tbl.findall(Wq + "tr")
        for i, tr in enumerate(rows):
            if _is_ra_header(tr):
                return tbl, i
    return None, None


def _looks_like_data_row(tr) -> bool:
    """A 10-cell data row: hazard | L | C | risk | controls | L | C | risk | result
    where the L/C cells are single digits."""
    cells = tr.findall(Wq + "tc")
    if len(cells) < 9:
        return False
    vals = [_cell_text(c) for c in cells]
    digits = [v for v in vals if v.isdigit()]
    return len(digits) >= 4


def fill_ssra(template_bytes: bytes, ra: dict) -> bytes:
    """Fill the company SSRA template with the generated risk assessment.

    Replaces the example hazard rows in the Risk Assessment table with one
    row per AI-identified hazard. Returns the new .docx as bytes.
    """
    zin = zipfile.ZipFile(io.BytesIO(template_bytes))
    names = zin.namelist()
    doc_xml = zin.read("word/document.xml")

    root = ET.fromstring(doc_xml)
    body = root.find(Wq + "body")
    tbl, hdr_idx = _find_ra_table_and_header(body)
    if tbl is None:
        zin.close()
        raise ValueError("Could not find a Risk Assessment table (Hazard / Pre-Control / "
                         "Control Measures / Post-Control / Result) in this template.")

    rows = tbl.findall(Wq + "tr")
    # Data rows are the data-shaped rows after the header row.
    data_rows = [(i, tr) for i, tr in enumerate(rows)
                 if i > hdr_idx and _looks_like_data_row(tr)]
    if not data_rows:
        zin.close()
        raise ValueError("Found the Risk Assessment table but no example data row to use as a template.")

    proto_tr = deepcopy(data_rows[0][1])

    # Detect the cell layout from the prototype using gridSpans:
    # narrow single cells are L/C/Risk/Result; the two wide spans are
    # Hazard (first wide) and Control Measures (second wide).
    proto_cells = proto_tr.findall(Wq + "tc")
    spans = [_gridspan(c) for c in proto_cells]
    wide_idx = [i for i, s in enumerate(spans) if s >= 3]
    hazard_ci = wide_idx[0] if wide_idx else 1
    controls_ci = wide_idx[1] if len(wide_idx) > 1 else 5
    # The four numeric cells sit either side of the controls cell.
    pre_cells = [i for i in range(len(proto_cells)) if hazard_ci < i < controls_ci]
    post_cells = [i for i in range(len(proto_cells)) if i > controls_ci]
    # Expect pre = [L, C, Risk]; post = [L, C, Risk, Result]
    while len(pre_cells) < 3:
        pre_cells.append(min(controls_ci - 1, len(proto_cells) - 1))

    hazards = ra.get("hazards") or []

    def build_row(hz: dict):
        tr = deepcopy(proto_tr)
        cells = tr.findall(Wq + "tc")

        def safe(ci):
            return cells[ci] if 0 <= ci < len(cells) else None

        # Hazard + potential harm (title then one line per harm)
        hcell = safe(hazard_ci)
        if hcell is not None:
            lines = [hz.get("hazard", "")]
            for h in (hz.get("potential_harm") or []):
                lines.append(h)
            _set_cell_lines(hcell, lines)

        # Pre-control numbers
        if len(pre_cells) >= 3:
            _set_cell_text(safe(pre_cells[0]), str(hz.get("pre_likelihood", "")))
            _set_cell_text(safe(pre_cells[1]), str(hz.get("pre_consequence", "")))
            _set_cell_text(safe(pre_cells[2]), str(hz.get("pre_rating", "")))

        # Control measures (one line each)
        ccell = safe(controls_ci)
        if ccell is not None:
            _set_cell_lines(ccell, hz.get("control_measures") or [""])

        # Post-control numbers + result
        if len(post_cells) >= 4:
            _set_cell_text(safe(post_cells[0]), str(hz.get("post_likelihood", "")))
            _set_cell_text(safe(post_cells[1]), str(hz.get("post_consequence", "")))
            _set_cell_text(safe(post_cells[2]), str(hz.get("post_rating", "")))
            _set_cell_text(safe(post_cells[3]), hz.get("result", ""))
        return tr

    # Build the replacement rows.
    new_rows = [build_row(hz) for hz in hazards] if hazards else [deepcopy(proto_tr)]

    # Splice: remove old data rows, insert new ones at the first data position.
    first_data_idx = data_rows[0][0]
    old_data_trs = [tr for _, tr in data_rows]
    for tr in old_data_trs:
        tbl.remove(tr)
    # Re-find children to compute the insertion anchor (header row).
    children = list(tbl)
    # Insert after the header row element.
    hdr_tr = rows[hdr_idx]
    insert_at = list(tbl).index(hdr_tr) + 1
    for off, tr in enumerate(new_rows):
        tbl.insert(insert_at + off, tr)

    decl = b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
    new_doc = decl + ET.tostring(root, xml_declaration=False, encoding="UTF-8")

    # Rewrite the zip with the modified document.xml, copying everything else.
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for name in names:
            data = new_doc if name == "word/document.xml" else zin.read(name)
            zout.writestr(name, data)
    zin.close()
    return out.getvalue()
