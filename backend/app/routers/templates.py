"""Templates API router."""

from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.schemas.template import TemplateListItem, TemplateResponse, TemplateUpdate

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("/", response_model=list[TemplateListItem])
async def list_templates() -> list[TemplateListItem]:
    """List all available templates."""
    template_dir = Path(settings.template_dir)
    if not template_dir.exists():
        return []

    items = []
    for category_dir in sorted(template_dir.iterdir()):
        if not category_dir.is_dir():
            continue
        for file in sorted(category_dir.iterdir()):
            if file.is_file() and file.suffix in (".html", ".txt"):
                items.append(
                    TemplateListItem(
                        category=category_dir.name,
                        filename=file.name,
                    )
                )
    return items


@router.get("/{category}/{filename}", response_model=TemplateResponse)
async def get_template(category: str, filename: str) -> TemplateResponse:
    """Get a template's content."""
    file_path = Path(settings.template_dir) / category / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Template nicht gefunden")

    # Prevent path traversal
    try:
        file_path.resolve().relative_to(Path(settings.template_dir).resolve())
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Ungültiger Pfad") from e

    return TemplateResponse(
        category=category,
        filename=filename,
        content=file_path.read_text(encoding="utf-8"),
    )


@router.put("/{category}/{filename}", response_model=TemplateResponse)
async def update_template(
    category: str,
    filename: str,
    data: TemplateUpdate,
) -> TemplateResponse:
    """Update a template's content."""
    file_path = Path(settings.template_dir) / category / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Template nicht gefunden")

    # Prevent path traversal
    try:
        file_path.resolve().relative_to(Path(settings.template_dir).resolve())
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Ungültiger Pfad") from e

    file_path.write_text(data.content, encoding="utf-8")
    return TemplateResponse(
        category=category,
        filename=filename,
        content=data.content,
    )
