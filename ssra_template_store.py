"""Store for company SSRA (Site Specific Risk Assessment) .docx templates.

Mirrors template_store.py (COSHH) but for the Risk Assessment module.
The built-in default is the sanitised company SSRA shipped in templates/.
Uploaded templates live under /tmp/ssra_templates/ in the app container.
"""

import os
import re
from pathlib import Path

TEMPLATE_DIR = Path("/tmp/ssra_templates")
BUILTIN_KEY = "_builtin_"
BUILTIN_DISPLAY = "Built-in company SSRA template"
_BUILTIN_PATH = Path(__file__).parent / "templates" / "ssra_template.docx"


def _ensure_dir() -> None:
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)


def _safe_name(name: str) -> str:
    name = os.path.basename(name)
    name = re.sub(r"[^A-Za-z0-9._\-]", "_", name)
    if not name.lower().endswith(".docx"):
        name = name + ".docx"
    return name


def list_templates() -> list[tuple[str, str]]:
    """Return (key, display_name) tuples — built-in first, then uploaded."""
    _ensure_dir()
    items = [(BUILTIN_KEY, BUILTIN_DISPLAY)]
    for f in sorted(TEMPLATE_DIR.glob("*.docx")):
        items.append((f.name, f.name))
    return items


def save_template(filename: str, data: bytes) -> str:
    _ensure_dir()
    key = _safe_name(filename)
    (TEMPLATE_DIR / key).write_bytes(data)
    return key


def get_template_bytes(key: str) -> bytes:
    if key == BUILTIN_KEY:
        return _BUILTIN_PATH.read_bytes()
    _ensure_dir()
    path = TEMPLATE_DIR / key
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {key}")
    return path.read_bytes()


def delete_template(key: str) -> None:
    if key == BUILTIN_KEY:
        return
    _ensure_dir()
    path = TEMPLATE_DIR / key
    if path.exists():
        path.unlink()
