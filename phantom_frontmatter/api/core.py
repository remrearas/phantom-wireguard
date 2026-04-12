"""
Phantom-WG Frontmatter — Core API Engine

The FrontmatterAPI class is the main orchestrator. It discovers modules
dynamically from phantom_frontmatter/modules/, instantiates them, and
provides a unified execute() interface along with attribute-style access
via ModuleProxy.

Architecture:
    api = FrontmatterAPI()
    response = api.execute("wstunnel", "enable")  # method style
    response = api.wstunnel.enable()               # proxy style

Each module directory under phantom_frontmatter/modules/ must contain:
    - module.py  → class that inherits from BaseModule
    - __init__.py

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0
"""

import importlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from phantom_frontmatter import __version__

from .exceptions import (
    FrontmatterException,
    FrontmatterModuleNotFoundError,
)
from .response import APIResponse


class FrontmatterAPI:
    """Main API orchestrator for Phantom-WG Frontmatter.

    Discovers and loads all modules from phantom_frontmatter/modules/,
    provides unified execution and introspection.

    Usage:
        api = FrontmatterAPI()

        # Direct execution
        response = api.execute("setup", "init", backend="203.0.113.5")

        # Proxy style
        response = api.ghost.start()
        response = api.ghost.client_config()

        # Introspection
        modules = api.list_modules()
        actions = api.list_actions("ghost")
    """

    def __init__(self, install_dir: Optional[Path] = None):
        """Initialize API and load all modules.

        Args:
            install_dir: Installation root directory
                         (default: /opt/phantom-frontmatter)
        """
        self.install_dir = install_dir or Path("/opt/phantom-frontmatter")
        self.version = __version__
        self.logger = logging.getLogger("phantom.frontmatter")
        self._modules: Dict[str, Any] = {}
        self._load_modules()

    # ── Module Discovery ──────────────────────────────────────────

    def _load_modules(self) -> None:
        """Dynamically discover and instantiate all modules.

        Scans phantom_frontmatter/modules/ for subdirectories containing
        a module.py file with a class inheriting from BaseModule.
        """
        from phantom_frontmatter.modules.base import BaseModule

        modules_pkg = "phantom_frontmatter.modules"
        modules_path = Path(__file__).parent.parent / "modules"

        if not modules_path.exists():
            self.logger.warning(f"Modules directory not found: {modules_path}")
            return

        for item in sorted(modules_path.iterdir()):
            # Skip non-directories and private
            if not item.is_dir() or item.name.startswith("_"):
                continue
            # Must contain module.py
            if not (item / "module.py").exists():
                continue

            module_name = item.name
            try:
                py_module = importlib.import_module(f"{modules_pkg}.{module_name}.module")
            except Exception as e:
                self.logger.error(f"Failed to import module {module_name!r}: {e}")
                continue

            # Find BaseModule subclass in the imported module
            module_class = None
            for attr_name in dir(py_module):
                attr = getattr(py_module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, BaseModule)
                    and attr is not BaseModule
                ):
                    module_class = attr
                    break

            if module_class is None:
                self.logger.warning(
                    f"No BaseModule subclass found in {module_name}/module.py"
                )
                continue

            try:
                # noinspection PyCallingNonCallable
                instance = module_class(install_dir=self.install_dir)
            except Exception as e:
                self.logger.error(f"Failed to instantiate {module_name}: {e}")
                continue

            # Use the module's declared name (may differ from directory name)
            declared_name = instance.get_module_name()
            self._modules[declared_name] = instance
            self.logger.debug(f"Loaded module: {declared_name}")

    # ── Execution ──────────────────────────────────────────────────

    def execute(self, module_name: str, action: str, **kwargs: Any) -> APIResponse:
        """Execute an action on a module.

        Args:
            module_name: Name of the module (e.g. "setup", "ghost")
            action:      Name of the action (e.g. "init", "start", "status")
            **kwargs:    Action-specific parameters

        Returns:
            APIResponse with success/data or error details.
        """
        if module_name not in self._modules:
            return APIResponse.fail(
                f"Module '{module_name}' not found. "
                f"Available: {', '.join(self._modules.keys()) or '(none)'}",
                code="MODULE_NOT_FOUND",
                module=module_name,
                action=action,
            )

        module = self._modules[module_name]
        try:
            actions = module.get_actions()
        except Exception as e:
            self.logger.exception(f"Failed to get actions for {module_name}")
            return APIResponse.fail(
                f"Module error: {e}",
                code="MODULE_ERROR",
                module=module_name,
                action=action,
            )

        if action not in actions:
            return APIResponse.fail(
                f"Action '{action}' not found in module '{module_name}'. "
                f"Available: {', '.join(actions.keys())}",
                code="ACTION_NOT_FOUND",
                module=module_name,
                action=action,
            )

        action_func = actions[action]
        try:
            result = action_func(**kwargs)
            # Action can return APIResponse directly or a dict
            if isinstance(result, APIResponse):
                if result.module is None:
                    result.module = module_name
                if result.action is None:
                    result.action = action
                return result
            return APIResponse.ok(
                data=result,
                module=module_name,
                action=action,
            )
        except FrontmatterException as e:
            self.logger.warning(
                f"[{module_name}.{action}] {e.code}: {e.message}"
            )
            return APIResponse.fail(
                e.message,
                code=e.code,
                module=module_name,
                action=action,
            )
        except TypeError as e:
            # Missing/extra arguments
            return APIResponse.fail(
                f"Invalid parameters for {module_name}.{action}: {e}",
                code="INVALID_PARAMS",
                module=module_name,
                action=action,
            )
        except Exception as e:
            self.logger.exception(f"Unexpected error in {module_name}.{action}")
            return APIResponse.fail(
                f"Unexpected error: {e}",
                code="UNEXPECTED_ERROR",
                module=module_name,
                action=action,
            )

    # ── Introspection ──────────────────────────────────────────────

    def list_modules(self) -> List[str]:
        """Return a list of loaded module names."""
        return sorted(self._modules.keys())

    def list_actions(self, module_name: str) -> List[str]:
        """Return a list of actions for a module.

        Raises:
            FrontmatterModuleNotFoundError: If module is not loaded.
        """
        if module_name not in self._modules:
            raise FrontmatterModuleNotFoundError(module_name)
        return sorted(self._modules[module_name].get_actions().keys())

    def get_module(self, module_name: str) -> Any:
        """Return the raw module instance.

        Raises:
            FrontmatterModuleNotFoundError: If module is not loaded.
        """
        if module_name not in self._modules:
            raise FrontmatterModuleNotFoundError(module_name)
        return self._modules[module_name]

    # ── Attribute-style access (proxy) ─────────────────────────────

    def __getattr__(self, name: str) -> "ModuleProxy":
        """Return a ModuleProxy for attribute-style action calls.

        Example:
            api.ghost.start()  ==  api.execute("ghost", "start")
        """
        # Prevent infinite recursion on private attributes
        if name.startswith("_"):
            raise AttributeError(name)
        if name not in self._modules:
            raise AttributeError(
                f"No module named {name!r}. "
                f"Available: {', '.join(self._modules.keys())}"
            )
        return ModuleProxy(self, name)


class ModuleProxy:
    """Proxy that provides attribute-style action execution.

    Example:
        proxy = ModuleProxy(api, "setup")
        proxy.init(backend="1.2.3.4")  # api.execute("setup", "init", ...)
        proxy = ModuleProxy(api, "ghost")
        proxy.start()                  # api.execute("ghost", "start")
    """

    def __init__(self, api: FrontmatterAPI, module_name: str):
        self._api = api
        self._module_name = module_name

    def __getattr__(self, action: str):
        if action.startswith("_"):
            raise AttributeError(action)

        def _execute(**kwargs: Any) -> APIResponse:
            return self._api.execute(self._module_name, action, **kwargs)

        _execute.__name__ = action
        return _execute

    def __repr__(self) -> str:
        return f"<ModuleProxy module={self._module_name!r}>"
