"""Module discovery API — exposes manifests and desktop data."""

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.utils.dependencies import get_current_tenant_id
from app.utils.module_registry import get_all_manifests, get_all_modules, get_manifest

router = APIRouter(prefix="/modules", tags=["modules"])

# Static modules without __manifest__.py but with frontend presence
STATIC_MODULES = [
    {
        "name": "n8n",
        "label": "n8n Workflows",
        "icon": "M6 13.5V3.75m0 9.75a1.5 1.5 0 010 3m0-3a1.5 1.5 0 000 3m0 3.75V16.5m12-3V3.75m0 9.75a1.5 1.5 0 010 3m0-3a1.5 1.5 0 000 3m0 3.75V16.5m-6-9V3.75m0 3.75a1.5 1.5 0 010 3m0-3a1.5 1.5 0 000 3m0 9.75V10.5",
        "color": "#D4A574",
        "category": "system",
        "application": True,
        "depends": [],
        "external_url": "https://n8n.go4.energy",
    },
    {
        "name": "dashboard",
        "label": "Dashboard",
        "icon": "M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zm0 9.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zm0 9.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25a2.25 2.25 0 01-2.25-2.25v-2.25z",
        "color": "#FF6600",
        "category": "system",
        "application": True,
        "depends": [],
        "frontend": {"base_route": "/dashboard"},
    },
]


@router.get("")
async def list_modules() -> list[dict]:
    """Return all module manifests (discovered + static)."""
    manifests = get_all_manifests()
    result = list(manifests.values()) + STATIC_MODULES
    return result


@router.get("/desktop")
async def get_desktop_modules(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return application modules with badge counts for desktop view."""
    manifests = get_all_manifests()
    interfaces = get_all_modules()
    result = []

    for name, manifest in manifests.items():
        if not manifest.get("application", False):
            continue

        entry = {
            "name": name,
            "label": manifest.get("label", name),
            "icon": manifest.get("icon", ""),
            "color": manifest.get("color", "#6B7280"),
            "category": manifest.get("category", ""),
            "order": manifest.get("sidebar", {}).get("order", 99),
            "badge_count": 0,
            "frontend": manifest.get("frontend"),
        }

        # Try to get badge count from module interface metrics
        interface = interfaces.get(name)
        if interface:
            try:
                metrics_data = await interface.get_metrics(db, tenant_id, days=7)
                metrics = metrics_data.get("metrics", {})
                entry["badge_count"] = _extract_badge_count(name, metrics)
            except Exception as e:
                logger.warning(
                    "Failed to get metrics for {name}: {err}",
                    name=name,
                    err=str(e),
                )

        result.append(entry)

    # Add static desktop modules
    for static_mod in STATIC_MODULES:
        if static_mod.get("application", False):
            result.append(
                {
                    "name": static_mod["name"],
                    "label": static_mod.get("label", static_mod["name"]),
                    "icon": static_mod.get("icon", ""),
                    "color": static_mod.get("color", "#6B7280"),
                    "category": static_mod.get("category", ""),
                    "badge_count": 0,
                    "frontend": static_mod.get("frontend"),
                    "external_url": static_mod.get("external_url"),
                }
            )

    # Sort: marketing first, then system; within category by order
    category_order = {"marketing": 0, "system": 1}
    result.sort(
        key=lambda m: (
            category_order.get(m.get("category", ""), 99),
            m.get("order", 99),
        )
    )
    return result


@router.get("/{name}")
async def get_module_detail(
    name: str,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return single module manifest with live status and metrics."""
    manifest = get_manifest(name)

    # Check static modules too
    if manifest is None:
        for static in STATIC_MODULES:
            if static["name"] == name:
                return static
        raise HTTPException(status_code=404, detail=f"Module '{name}' not found")

    result = dict(manifest)
    interfaces = get_all_modules()
    interface = interfaces.get(name)

    if interface:
        try:
            result["status"] = await interface.get_status(db, tenant_id)
        except Exception as e:
            logger.warning(
                "Status fetch failed for {name}: {err}", name=name, err=str(e)
            )
            result["status"] = {"healthy": False, "error": str(e)}

        try:
            result["metrics"] = await interface.get_metrics(db, tenant_id, days=7)
        except Exception as e:
            logger.warning(
                "Metrics fetch failed for {name}: {err}", name=name, err=str(e)
            )
            result["metrics"] = {}

    return result


def _extract_badge_count(module_name: str, metrics: dict) -> int:
    """Extract a meaningful badge count from module metrics."""
    badge_keys = {
        "collector": "findings_total",
        "creator": "pieces_draft",
        "distributor": "active_campaigns",
        "crm": "contacts_active",
        "briefing": "active_channels",
    }
    key = badge_keys.get(module_name)
    if key and key in metrics:
        return metrics[key]
    return 0
