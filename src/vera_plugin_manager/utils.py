import sys
import inspect
import importlib.util
from pathlib import Path
from types import ModuleType

from vera_plugin_interface import BaseEvaluationPlugin


def get_latest_py_timestamp(root_folder: str | Path) -> float | None:
    """Get the latest modification timestamp of all Python files in the given directory.

    Args:
        root_folder: The root directory (str or Path) to search for Python files.

    Returns:
        The modification timestamp (Unix epoch seconds) of the most recent .py file,
        or None if no Python files are found.
    """
    root = Path(root_folder)

    if not root.exists():
        raise FileNotFoundError(f"{root} does not exist")
    if not root.is_dir():
        raise NotADirectoryError(f"{root} is not a directory")

    files = (p.stat().st_mtime for p in Path(root_folder).rglob("*.py") if p.is_file())
    return max(files, default=None)


def find_installable_packages(
    root_dirs: str | Path | list[str | Path],
) -> list[Path]:
    """
    Recursively search one or more directories for pip-installable Python projects,
    pruning traversal into subdirectories once an installable project is found.

    Args:
        root_dirs (str | Path | list[str | Path]): One or more directories to search.

    Returns:
        list[str]: Absolute paths to all discovered projects (no duplicates).
    """
    projects: set[Path] = set()

    roots = [root_dirs] if isinstance(root_dirs, (str, Path)) else list(root_dirs)

    for root in roots:
        root = Path(root)
        if not root.exists() or not root.is_dir():
            continue
        for path in root.iterdir():
            if path.is_dir():
                if (path / "setup.py").exists() or (path / "pyproject.toml").exists():
                    projects.add(path.resolve())
                else:
                    projects.update(find_installable_packages(path))
    return list(projects)


def find_package_dir(project_root: str | Path) -> Path | None:
    """
    Return the first package directory under the project root.

    Looks for folders containing ``__init__.py`` in either:
    - <root>/src/
    - <root>/

    Raises:
        RuntimeError: If no package is found.
    """
    root = Path(project_root).resolve()

    # candidate bases
    candidates = [root / "src", root]

    for base in candidates:
        if not base.exists() or not base.is_dir():
            continue

        for child in base.iterdir():
            if child.is_dir() and (child / "__init__.py").exists():
                return child

    # raise RuntimeError("Could not find a package with __init__.py")
    return None


def load_package_from_dir(package_dir: str | Path) -> ModuleType:
    """
    Load a package from a directory without installing it.

    Executes ``__init__.py`` and enables relative imports.

    Raises:
        FileNotFoundError: If ``__init__.py`` is missing.
        ImportError: If loading fails.
    """
    package_dir = Path(package_dir)
    init_file = package_dir / "__init__.py"
    module_name = package_dir.name

    spec = importlib.util.spec_from_file_location(
        module_name,
        init_file,
        submodule_search_locations=[str(package_dir)],
    )

    if spec is None:
        raise ImportError(f"Could not create a module spec for {init_file}")
    if spec.loader is None:
        raise ImportError(f"No loader available for module {module_name}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module

    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise

    return module


def get_plugins(module: ModuleType) -> dict[str, type[BaseEvaluationPlugin]]:
    """
    Return all classes available on a module that inherit from BaseEvaluationPlugin
    """
    return {
        name: obj
        for name, obj in inspect.getmembers(module, inspect.isclass)
        if issubclass(obj, BaseEvaluationPlugin) and obj is not BaseEvaluationPlugin
    }


def get_plugins_from_package_path(
    project_root: str | Path,
) -> tuple[str, dict[str, type[BaseEvaluationPlugin]]] | None:
    module_dir = find_package_dir(project_root)
    if module_dir is None:
        return None
    module = load_package_from_dir(module_dir)
    # FIXME: use pyproject.toml or setup.py to get the module name
    return module_dir.name, get_plugins(module)
