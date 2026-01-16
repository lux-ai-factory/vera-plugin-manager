import importlib
import inspect
import sys
from pathlib import Path
from typing import Dict

from a4s_plugin_interface.base_evaluation_plugin import BaseEvaluationPlugin

plugin_path = 'plugins'

def find_module_directory(pkg_root: Path) -> Path | None:
    if (pkg_root / "__init__.py").exists():
        return pkg_root

    for subdirectory in pkg_root.iterdir():
        if not subdirectory.is_dir():
            continue

        if (subdirectory / "__init__.py").exists():
            return subdirectory

    return None

class Loader(str):
    def __init__(self, local_plugin_path: str):
        self.plugin_dirs = [Path(local_plugin_path), Path(plugin_path)]
        self.plugins: Dict[str, type[BaseEvaluationPlugin]] = {}
        self.load_plugin()

    def load_plugin(self):
        for plugin_dir in self.plugin_dirs:
            if not plugin_dir.exists() or not plugin_dir.is_dir():
                continue
            for pkg_root in plugin_dir.iterdir():
                if not pkg_root.exists() or not pkg_root.is_dir():
                    continue
                module_path = find_module_directory(pkg_root)
                if module_path:
                    sys.path.insert(0, str(pkg_root))

                    module_name = module_path.name
                    module = importlib.import_module(module_name)

                    for _, obj in inspect.getmembers(module, inspect.isclass):
                        if issubclass(obj, BaseEvaluationPlugin) and obj is not BaseEvaluationPlugin:
                            self.plugins[obj.__name__] = obj

    def list_plugins(self):
        return self.plugins

    def load(self, name: str) -> BaseEvaluationPlugin:
        cls = self.plugins.get(name)
        if not cls:
            raise KeyError(f"Plugin {name} not found")
        return cls()
