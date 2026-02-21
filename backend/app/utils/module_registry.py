"""Centralized module registry for auto-discovery of domain modules."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.utils.module_interface import ModuleInterface

_registry: dict[str, ModuleInterface] = {}


def register_module(interface: ModuleInterface) -> None:
    """Register a module interface for discovery by the settings system."""
    _registry[interface.MODULE_NAME] = interface


def get_all_modules() -> dict[str, ModuleInterface]:
    """Return all registered module interfaces."""
    return dict(_registry)


def get_module(name: str) -> ModuleInterface | None:
    """Return a single module interface by name."""
    return _registry.get(name)
