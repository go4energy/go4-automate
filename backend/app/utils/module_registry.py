"""Centralized module registry for auto-discovery of domain modules."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.utils.module_interface import ModuleInterface

_registry: dict[str, ModuleInterface] = {}
_manifests: dict[str, dict] = {}


def register_module(interface: ModuleInterface) -> None:
    """Register a module interface for discovery by the settings system."""
    _registry[interface.MODULE_NAME] = interface


def get_all_modules() -> dict[str, ModuleInterface]:
    """Return all registered module interfaces."""
    return dict(_registry)


def get_module(name: str) -> ModuleInterface | None:
    """Return a single module interface by name."""
    return _registry.get(name)


def register_manifest(name: str, manifest: dict) -> None:
    """Register a module manifest from auto-discovery."""
    _manifests[name] = manifest


def get_all_manifests() -> dict[str, dict]:
    """Return all registered module manifests."""
    return dict(_manifests)


def get_manifest(name: str) -> dict | None:
    """Return a single module manifest by name."""
    return _manifests.get(name)
