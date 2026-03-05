"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.

Production packager — builds dist/phantom-daemon/ with deployment-ready files.

Usage:
    python scripts/packager.py
    python scripts/packager.py --tar
    python scripts/packager.py --clean --tar
"""

from __future__ import annotations

import argparse
import shutil
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
PKG_NAME = "phantom-daemon"

# Files and directories to copy
INCLUDE_FILES = [
    "phantom_daemon/",
    "Dockerfile",
    "docker-compose.yml",
    "requirements.in",
    "requirements.txt",
    "tools/prod.sh",
    "tools/gen-keys.sh",
]

# Empty directories to create
EMPTY_DIRS = [
    "services/auth-service",
    "container-data/secrets/production",
    "container-data/auth-db",
    "container-data/db",
    "container-data/state/db",
]

EXCLUDE_SUFFIXES = (".pyc", ".pyo")


def _should_exclude(path: Path) -> bool:
    return "__pycache__" in path.parts or path.suffix in EXCLUDE_SUFFIXES


def _copy_entry(src: Path, dst: Path) -> int:
    count = 0
    if src.is_file():
        if _should_exclude(src) or src.name == ".gitkeep":
            return 0
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return 1

    for item in sorted(src.rglob("*")):
        if not item.is_file() or _should_exclude(item) or item.name == ".gitkeep":
            continue
        rel = item.relative_to(src)
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
        count += 1
    return count


def package(clean: bool = False, tar: bool = False) -> Path:
    pkg_dir = DIST / PKG_NAME

    if clean and DIST.exists():
        shutil.rmtree(DIST)

    pkg_dir.mkdir(parents=True, exist_ok=True)

    total = 0
    for entry in INCLUDE_FILES:
        src = ROOT / entry
        if not src.exists():
            print(f"  SKIP (not found): {entry}")
            continue
        dst = pkg_dir / entry
        count = _copy_entry(src, dst)
        total += count
        print(f"  {entry} ({count} files)")

    for d in EMPTY_DIRS:
        (pkg_dir / d).mkdir(parents=True, exist_ok=True)
        print(f"  {d}/ (empty dir)")

    # Make scripts executable
    for name in ("tools/prod.sh", "tools/gen-keys.sh"):
        script = pkg_dir / name
        if script.exists():
            script.chmod(0o755)

    print(f"\nTotal: {total} files → {pkg_dir}")

    if tar:
        tar_path = DIST / f"{PKG_NAME}.tar.gz"
        with tarfile.open(tar_path, "w:gz") as tf:
            tf.add(pkg_dir, arcname=PKG_NAME)
        size_kb = tar_path.stat().st_size / 1024
        print(f"Archive: {tar_path} ({size_kb:.1f} KB)")
        return tar_path

    return pkg_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Package phantom-daemon for production")
    parser.add_argument("--clean", action="store_true", help="Remove dist/ before packaging")
    parser.add_argument("--tar", action="store_true", help="Create .tar.gz archive")
    args = parser.parse_args()
    package(clean=args.clean, tar=args.tar)


if __name__ == "__main__":
    main()
