"""Controlled module documentation registry and loader.

Resolution order for a given module name:
  1. Explicit MODULE_DOCS registry entry (file under /docs)
  2. Auto-fallback: backend/app/<name>/README.md

The fallback lets each module ship its own README without needing a registry
entry — keeps Single Source of Truth in the module folder.
"""

from pathlib import Path

from app.exceptions import NotFoundError

REPO_ROOT = Path(__file__).resolve().parents[3]
DOCS_ROOT = REPO_ROOT / "docs"
APP_ROOT = REPO_ROOT / "backend" / "app"

MODULE_DOCS: dict[str, dict[str, str]] = {
    "assistant": {
        "title": "Assistant Dokumentation",
        "path": "ASSISTANT-EMAIL-POLICY-SPEC.md",
    },
}


def get_module_doc(name: str) -> dict[str, str]:
    """Return documentation metadata and markdown content for a module."""
    entry = MODULE_DOCS.get(name)
    if entry:
        doc_path = DOCS_ROOT / entry["path"]
        if doc_path.exists():
            return {
                "module": name,
                "title": entry["title"],
                "path": entry["path"],
                "content": doc_path.read_text(encoding="utf-8"),
            }

    # Auto-fallback: backend/app/<name>/README.md
    readme_path = APP_ROOT / name / "README.md"
    if readme_path.exists():
        return {
            "module": name,
            "title": f"{name.capitalize()} Dokumentation",
            "path": f"app/{name}/README.md",
            "content": readme_path.read_text(encoding="utf-8"),
        }

    raise NotFoundError("ModuleDocumentation", name)
