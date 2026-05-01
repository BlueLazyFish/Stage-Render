#!/usr/bin/env python3
"""Build the Stage extension zip for local install or extensions.blender.org submission.

Usage:
    python scripts/package.py [--out PATH]

The output is a zip whose root contains blender_manifest.toml and __init__.py
(Blender's expected layout — not a zip of the `stage/` folder, but of its contents).
"""

from __future__ import annotations

import argparse
import sys
import tomllib
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
ADDON_DIR = REPO_ROOT / "stage"
DEFAULT_OUT = REPO_ROOT / "build"


def _read_manifest() -> dict:
    with (ADDON_DIR / "blender_manifest.toml").open("rb") as f:
        return tomllib.load(f)


def _should_include(path: Path) -> bool:
    for part in path.parts:
        if part in {"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"}:
            return False
    if path.name == ".DS_Store" or path.name.endswith((".pyc", ".pyo")):
        return False
    return True


def build(out_dir: Path) -> Path:
    manifest = _read_manifest()
    name = manifest["id"]
    version = manifest["version"]

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{name}-{version}.zip"

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(ADDON_DIR.rglob("*")):
            if not path.is_file() or not _should_include(path):
                continue
            zf.write(path, arcname=path.relative_to(ADDON_DIR))

    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--out", type=Path, default=DEFAULT_OUT,
        help=f"Output directory (default: ./{DEFAULT_OUT.relative_to(REPO_ROOT)}/)",
    )
    args = parser.parse_args()

    out = build(args.out.resolve())
    print(f"Built: {out}")
    print("Install via: Blender > Edit > Preferences > Get Extensions > Install from Disk")
    return 0


if __name__ == "__main__":
    sys.exit(main())
