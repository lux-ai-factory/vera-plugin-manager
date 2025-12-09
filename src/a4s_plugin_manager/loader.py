import importlib
import inspect
import sys
from pathlib import Path
from typing import Dict

from a4s_plugin_interface import EvaluationPluginInterface

core_plugin_path = 'plugins/core'

class Loader(str):
    def __init__(self, dev_plugin_path: str):
        self.plugin_dirs = [Path(dev_plugin_path), Path(core_plugin_path)]
        self.plugins: Dict[str, type[EvaluationPluginInterface]] = {}
        self.load_plugin()

    def load_plugin(self):
        for plugin_dir in self.plugin_dirs:
            for pkg_root in plugin_dir.iterdir():
                if pkg_root.is_dir():
                    module_folder = pkg_root / pkg_root.name.replace("-", "_")

                    sys.path.insert(0, str(pkg_root))

                    module_name = module_folder.name
                    module = importlib.import_module(module_name)

                    for _, obj in inspect.getmembers(module, inspect.isclass):
                        if issubclass(obj, EvaluationPluginInterface) and obj is not EvaluationPluginInterface:
                            self.plugins[obj.__name__] = obj

    def list_plugins(self):
        return self.plugins

    def load(self, name: str) -> EvaluationPluginInterface:
        cls = self.plugins.get(name)
        if not cls:
            raise KeyError(f"Plugin {name} not found")
        return cls()
