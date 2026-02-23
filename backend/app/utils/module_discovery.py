"""Auto-discovery engine for domain modules with __manifest__.py."""

from __future__ import annotations

import importlib
from pathlib import Path

from loguru import logger

from app.utils.module_registry import register_manifest


def discover_manifests(app_dir: Path) -> list[dict]:
    """Scan app_dir for directories with __manifest__.py, return topologically sorted list."""
    modules: dict[str, dict] = {}

    for manifest_path in app_dir.glob("*/__manifest__.py"):
        module_name = manifest_path.parent.name

        # Skip non-module directories
        if module_name.startswith("_") or module_name in (
            "utils",
            "routers",
            "models",
            "services",
        ):
            continue

        try:
            mod = importlib.import_module(f"app.{module_name}.__manifest__")
            manifest = getattr(mod, "manifest", None)
            if manifest is None:
                logger.warning(
                    "No 'manifest' dict in app.{name}.__manifest__", name=module_name
                )
                continue

            modules[module_name] = {
                "name": module_name,
                "path": str(manifest_path.parent),
                "manifest": manifest,
            }
            register_manifest(module_name, manifest)
            logger.debug("Discovered module: {name}", name=module_name)
        except Exception as e:
            logger.error(
                "Failed to load manifest for {name}: {err}",
                name=module_name,
                err=str(e),
            )

    # Topological sort by depends
    sorted_modules = _topological_sort(modules)
    logger.info(
        "Discovered {count} modules: {names}",
        count=len(sorted_modules),
        names=[m["name"] for m in sorted_modules],
    )
    return sorted_modules


def _topological_sort(modules: dict[str, dict]) -> list[dict]:
    """Sort modules by their dependency graph (depends field in manifest)."""
    visited: set[str] = set()
    result: list[dict] = []

    def visit(name: str) -> None:
        if name in visited or name not in modules:
            return
        visited.add(name)
        depends = modules[name]["manifest"].get("depends", [])
        for dep in depends:
            visit(dep)
        result.append(modules[name])

    for name in modules:
        visit(name)

    return result


def register_routers(app, manifests: list[dict], prefix: str = "/api/v1") -> None:
    """Import and register routers for all discovered modules."""
    from fastapi import FastAPI

    if not isinstance(app, FastAPI):
        raise TypeError("app must be a FastAPI instance")

    for entry in manifests:
        name = entry["name"]
        manifest = entry["manifest"]
        router_names = manifest.get("routers", [])

        for router_name in router_names:
            try:
                mod = importlib.import_module(f"app.{name}.{router_name}")
                router = getattr(mod, "router", None)
                if router is None:
                    logger.warning(
                        "No 'router' in app.{name}.{rn}", name=name, rn=router_name
                    )
                    continue
                app.include_router(router, prefix=prefix)
                logger.debug(
                    "Registered router: app.{name}.{rn}", name=name, rn=router_name
                )
            except Exception as e:
                logger.error(
                    "Failed to register router app.{name}.{rn}: {err}",
                    name=name,
                    rn=router_name,
                    err=str(e),
                )


def register_models(manifests: list[dict]) -> None:
    """Import models for all modules with has_models=True."""
    for entry in manifests:
        name = entry["name"]
        manifest = entry["manifest"]

        if not manifest.get("has_models", False):
            continue

        try:
            importlib.import_module(f"app.{name}.models")
            logger.debug("Registered models for: {name}", name=name)
        except Exception as e:
            logger.error(
                "Failed to import models for {name}: {err}", name=name, err=str(e)
            )


def register_interfaces(manifests: list[dict]) -> None:
    """Import config_schema for all modules with has_config_schema=True."""
    for entry in manifests:
        name = entry["name"]
        manifest = entry["manifest"]

        if not manifest.get("has_config_schema", False):
            continue

        try:
            importlib.import_module(f"app.{name}.config_schema")
            logger.debug("Registered config interface for: {name}", name=name)
        except Exception as e:
            logger.error(
                "Failed to import config_schema for {name}: {err}",
                name=name,
                err=str(e),
            )
