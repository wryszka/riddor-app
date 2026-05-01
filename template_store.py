"""Local filesystem-based COSHH template store.

Templates live under /tmp/coshh_templates/ in the app container.
The built-in default template is generated on the fly and always
appears in the list with the special name "_builtin_".
"""

import os
import re
from pathlib import Path

TEMPLATE_DIR = Path("/tmp/coshh_templates")
BUILTIN_KEY = "_builtin_"
BUILTIN_DISPLAY = "Built-in COSHH template"


def _ensure_dir() -> None:
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)


def _safe_name(name: str) -> str:
    """Sanitise a filename — strip path components, keep alnum/dot/dash/underscore."""
    name = os.path.basename(name)
    name = re.sub(r"[^A-Za-z0-9._\-]", "_", name)
    if not name.lower().endswith(".docx"):
        name = name + ".docx"
    return name


def list_templates() -> list[tuple[str, str]]:
    """Return list of (key, display_name) tuples — built-in first, then uploaded."""
    _ensure_dir()
    items = [(BUILTIN_KEY, BUILTIN_DISPLAY)]
    for f in sorted(TEMPLATE_DIR.glob("*.docx")):
        items.append((f.name, f.name))
    return items


def save_template(filename: str, data: bytes) -> str:
    """Save an uploaded template; return the key it's stored under."""
    _ensure_dir()
    key = _safe_name(filename)
    (TEMPLATE_DIR / key).write_bytes(data)
    return key


def get_template_bytes(key: str) -> bytes:
    """Load a template's bytes. Raises if not found."""
    if key == BUILTIN_KEY:
        from coshh_default_template import build_default_template
        return build_default_template()
    _ensure_dir()
    path = TEMPLATE_DIR / key
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {key}")
    return path.read_bytes()


def delete_template(key: str) -> None:
    """Remove an uploaded template (built-in cannot be removed)."""
    if key == BUILTIN_KEY:
        return
    _ensure_dir()
    path = TEMPLATE_DIR / key
    if path.exists():
        path.unlink()
