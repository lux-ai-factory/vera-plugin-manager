import importlib
import inspect
import sys
import logging
from pathlib import Path
from typing import Dict

from a4s_plugin_interface.base_evaluation_plugin import BaseEvaluationPlugin

logger = logging.getLogger(__name__)
plugin_path = "plugins"


def find_module_directory(pkg_root: Path) -> Path | None:
    """
    Strictly checks for:
    1. pkg_root/module_name/__init__.py
    2. pkg_root/src/module_name/__init__.py
    """
    # Case 2: src/module structure
    src_dir = pkg_root / "src"
    if src_dir.exists() and src_dir.is_dir():
        for subdirectory in src_dir.iterdir():
            if subdirectory.is_dir() and (subdirectory / "__init__.py").exists():
                return subdirectory

    # Case 1: Direct module structure
    for subdirectory in pkg_root.iterdir():
        if subdirectory.is_dir() and (subdirectory / "__init__.py").exists():
            return subdirectory

    return None


class Loader:
    def __init__(self, local_plugin_path: str):
        self.plugin_dirs = [Path(local_plugin_path), Path(plugin_path)]
        self.plugins: Dict[str, type[BaseEvaluationPlugin]] = {}
        self._find_plugins()

    def _find_plugins(self):
        self.plugins = {}
        for plugin_dir in self.plugin_dirs:
            if not plugin_dir.exists() or not plugin_dir.is_dir():
                continue

            for pkg_root in plugin_dir.iterdir():
                if not pkg_root.is_dir():
                    continue

                module_path = find_module_directory(pkg_root)
                if module_path:
                    # module_path is the directory containing __init__.py
                    # its parent is what needs to be in sys.path
                    parent_path = str(module_path.parent)
                    if parent_path not in sys.path:
                        sys.path.insert(0, parent_path)

                    module_name = module_path.name
                    try:
                        # Reload to capture changes in code during runtime
                        if module_name in sys.modules:
                            modules_to_remove = [
                                m
                                for m in sys.modules
                                if m == module_name or m.startswith(f"{module_name}.")
                            ]
                            for m in modules_to_remove:
                                del sys.modules[m]

                        module = importlib.import_module(module_name)

                        for _, obj in inspect.getmembers(module, inspect.isclass):
                            if (
                                issubclass(obj, BaseEvaluationPlugin)
                                and obj is not BaseEvaluationPlugin
                            ):
                                self.plugins[obj.display_name] = obj
                    except Exception as e:
                        logger.error(
                            f"Failed to load plugin {module_name} from {pkg_root}: {e}"
                        )

    def list_plugins(self):
        self._find_plugins()
        return self.plugins

    def load(self, name: str) -> BaseEvaluationPlugin:
        self._find_plugins()
        cls = self.plugins.get(name)
        if not cls:
            raise KeyError(f"Plugin {name} not found")
        return cls()
