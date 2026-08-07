from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from .section_manifest import PROJECT_ROOT, SECTION_FILES, SECTION_MODULES

ROOT_DIR = PROJECT_ROOT

_namespace: dict[str, Any] | None = None
_modules: dict[str, ModuleType] | None = None


def _public_symbols(module_dict: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in module_dict.items()
        if not key.startswith("__")
    }


def _build_module(section_file: Path, module_name: str, shared: dict[str, Any]) -> ModuleType:
    module = ModuleType(module_name)
    module.__file__ = str(section_file)
    module.__package__ = module_name.rpartition(".")[0]
    module.__loader_mode__ = "module-runtime"
    module.__dict__["__builtins__"] = __builtins__
    module.__dict__.update(shared)
    sys.modules[module_name] = module

    package_name, _, child_name = module_name.rpartition(".")
    if package_name:
        parent_module = importlib.import_module(package_name)
        setattr(parent_module, child_name, module)

    code = section_file.read_text(encoding="utf-8")
    exec(compile(code, str(section_file), "exec"), module.__dict__, module.__dict__)
    return module


def _sync_shared_symbols(shared: dict[str, Any], modules: dict[str, ModuleType]) -> None:
    for module in modules.values():
        module.__dict__.update(shared)


def sync_runtime_bindings(source: dict[str, Any], names: list[str] | None = None) -> dict[str, Any]:
    """Propagate runtime global re-bindings from one loaded module to all others."""
    global _namespace, _modules

    if _modules is None:
        return {}

    if names is None:
        updates = _public_symbols(source)
    else:
        updates = {name: source[name] for name in names if name in source}

    if not updates:
        return {}

    if _namespace is not None:
        _namespace.update(updates)

    for module in _modules.values():
        module.__dict__.update(updates)

    return updates


def _unload_runtime_modules() -> None:
    for module_name in SECTION_MODULES:
        existing = sys.modules.get(module_name)
        if existing is not None and getattr(existing, "__loader_mode__", None) == "module-runtime":
            package_name, _, child_name = module_name.rpartition(".")
            if package_name:
                parent_module = sys.modules.get(package_name)
                if parent_module is not None and getattr(parent_module, child_name, None) is existing:
                    delattr(parent_module, child_name)
            sys.modules.pop(module_name, None)


def build_namespace() -> dict[str, Any]:
    shared: dict[str, Any] = {
        "__loader_mode__": "module-runtime",
        "__root_dir__": str(ROOT_DIR),
    }
    loaded_modules: dict[str, ModuleType] = {}

    _unload_runtime_modules()

    for section_file, module_name in zip(SECTION_FILES, SECTION_MODULES):
        module = _build_module(section_file, module_name, shared)
        loaded_modules[module_name] = module
        shared.update(_public_symbols(module.__dict__))
        _sync_shared_symbols(shared, loaded_modules)

    namespace = dict(shared)
    namespace["__modules__"] = loaded_modules
    namespace["__loader_mode__"] = "module-runtime"
    return namespace


def load_modules(force_reload: bool = False) -> dict[str, ModuleType]:
    global _modules, _namespace
    if force_reload or _modules is None:
        _namespace = build_namespace()
        _modules = dict(_namespace.get("__modules__", {}))
    return _modules


def load_namespace(force_reload: bool = False) -> dict[str, Any]:
    global _namespace, _modules
    if force_reload or _namespace is None:
        _namespace = build_namespace()
        _modules = dict(_namespace.get("__modules__", {}))
    return _namespace
