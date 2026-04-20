import logging
from pathlib import Path

from vera_plugin_interface import BaseEvaluationPlugin

from .utils import find_installable_packages, get_plugins_from_package_path

logger = logging.getLogger(__name__)
plugin_path = "plugins"


class Loader:
    def __init__(self, local_plugin_path: str):
        self.plugin_dirs: list[str | Path] = [
            Path(local_plugin_path),
            Path(plugin_path),
        ]
        self.packages: dict[str, dict] = {}
        self.plugins: dict[str, type[BaseEvaluationPlugin]] = {}
        self.plugins2packages: dict[str, str] = {}
        self._find_plugins()

    def _find_plugins(self):
        self.plugins = {}
        self.packages = {}
        self.plugins2packages = {}

        for pkg_path in find_installable_packages(self.plugin_dirs):
            pkg_path = str(pkg_path)

            try:
                res = get_plugins_from_package_path(pkg_path)
                if res is None:
                    continue
                pkg_name, plugins = res
                # plugins.keys() are the class names of the Plugins
                named_plugins = {obj.display_name: obj for obj in plugins.values()}

                for plugin_name in named_plugins:
                    self.plugins2packages[plugin_name] = pkg_name

            except Exception as e:
                logger.error(f"Failed to load plugins in {pkg_path}: {e}")

            self.plugins.update(named_plugins)
            self.packages[pkg_name] = dict(name=pkg_name, path=pkg_path)

    def list_plugins(self):
        self._find_plugins()
        return self.plugins

    def load(self, name: str) -> BaseEvaluationPlugin:
        self._find_plugins()
        cls = self.plugins.get(name)
        if not cls:
            raise KeyError(f"Plugin {name} not found")
        return cls()

    def get_package(self, plugin_name: str) -> dict:
        """
        This method should be called after load (no _find_plugins call here)
        """
        pkg_name = self.plugins2packages.get(plugin_name)
        if not pkg_name:
            raise KeyError(f"No Package was found for Plugin {plugin_name}")
        pkg = self.packages.get(pkg_name)
        if not pkg:
            raise KeyError(f"Package {pkg_name} not found")
        return pkg
