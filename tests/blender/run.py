"""Run Stage's Blender-side tests.

Usage:
    blender -b -P tests/blender/run.py

Discovers test_*.py files in this directory and runs all functions named
test_*. Exits with status 0 on success, 1 on any failure. Registers the
Stage addon before tests run so bpy.context.scene.stage_data is wired up.
"""

from __future__ import annotations

import importlib.util
import sys
import traceback
from pathlib import Path


def _ensure_repo_on_path() -> Path:
    here = Path(__file__).resolve()
    repo_root = here.parent.parent.parent
    sys.path.insert(0, str(repo_root))
    return repo_root


def _register_addon() -> None:
    """Import and register Stage so PropertyGroups attach to Scene."""
    import stage  # noqa: PLC0415

    stage.register()


def _discover():
    """Yield (module_name, test_name, callable) for every test_* function
    in every test_*.py file alongside this runner."""
    test_dir = Path(__file__).resolve().parent
    for path in sorted(test_dir.glob("test_*.py")):
        spec = importlib.util.spec_from_file_location(path.stem, path)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for name in sorted(dir(module)):
            if name.startswith("test_") and callable(getattr(module, name)):
                yield path.stem, name, getattr(module, name)


def main() -> int:
    _ensure_repo_on_path()
    _register_addon()

    failures: list[tuple[str, str]] = []
    passed = 0

    for module_name, test_name, func in _discover():
        full = f"{module_name}::{test_name}"
        try:
            func()
            print(f"  PASS  {full}")
            passed += 1
        except Exception as e:  # noqa: BLE001 — test runner needs to catch all
            print(f"  FAIL  {full}: {type(e).__name__}: {e}")
            print(traceback.format_exc())
            failures.append((module_name, test_name))

    print()
    print(f"  {passed} passed, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
