#!/usr/bin/env python3
"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details

Vendor pack builder — creates per-architecture zip files from dev/vendor
branch contents. Each bridge's .so, .sha256, and Python package are
combined into a flat layout where _ffi.py finds the .so via sibling path.

Output goes to dist/ directory.

Usage:
    python packager.py v1.0.0
    python packager.py v1.0.0 --dry-run
"""

import argparse
import hashlib
import shutil
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
DIST_DIR = REPO_ROOT / "dist"

ARCHITECTURES = ["linux-amd64", "linux-arm64"]

BRIDGES = {
    "wireguard-go-bridge": {
        "so": "wireguard_go_bridge.so",
        "sha256": "wireguard_go_bridge.so.sha256",
        "package": "wireguard_go_bridge",
        "extras": [],
    },
    "firewall-bridge": {
        "so": "libfirewall_bridge_linux.so",
        "sha256": "libfirewall_bridge_linux.so.sha256",
        "package": "firewall_bridge",
        "extras": ["firewall_bridge_linux.h"],
    },
    "wstunnel-bridge": {
        "so": "libwstunnel_bridge_linux.so",
        "sha256": "libwstunnel_bridge_linux.so.sha256",
        "package": "wstunnel_bridge",
        "extras": [],
    },
}


def validate_sources(arch):
    """Check that all required source files exist for given architecture."""
    errors = []
    for bridge, spec in BRIDGES.items():
        base = REPO_ROOT / bridge / arch
        if not base.is_dir():
            errors.append(f"Missing: {base}")
            continue
        for name in [spec["so"], spec["sha256"]] + spec["extras"]:
            if not (base / name).is_file():
                errors.append(f"Missing: {base / name}")
        pkg = base / spec["package"]
        if not pkg.is_dir():
            errors.append(f"Missing: {pkg}")
        elif not list(pkg.glob("*.py")):
            errors.append(f"No .py files in: {pkg}")
    return errors


def verify_checksums(arch):
    """Verify .so checksums match .sha256 files."""
    errors = []
    for bridge, spec in BRIDGES.items():
        base = REPO_ROOT / bridge / arch
        so_path = base / spec["so"]
        sha_path = base / spec["sha256"]
        if not so_path.is_file() or not sha_path.is_file():
            continue
        actual = hashlib.sha256(so_path.read_bytes()).hexdigest()
        expected = sha_path.read_text().strip().split()[0]
        if actual != expected:
            errors.append(f"{bridge}/{arch}: expected {expected}, got {actual}")
    return errors


def build_zip(version, arch, dry_run=False):
    """
    Build vendor-pack zip for given architecture.

    Zip layout (flat, sibling path discovery):
        <package>/
            VERSION
            *.py
            <lib>.so
            <lib>.so.sha256
            <extras>
    """
    zip_name = f"vendor-pack-{version}-{arch}.zip"
    zip_path = DIST_DIR / zip_name

    if dry_run:
        print(f"  [dry-run] Would create: {zip_path}")
        return zip_path

    DIST_DIR.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for bridge, spec in BRIDGES.items():
            base = REPO_ROOT / bridge / arch
            pkg_name = spec["package"]
            version_file = REPO_ROOT / bridge / "VERSION"

            # VERSION inside package directory
            if version_file.is_file():
                zf.write(version_file, f"{pkg_name}/VERSION")

            # .so inside package directory
            zf.write(base / spec["so"], f"{pkg_name}/{spec['so']}")

            # .sha256 inside package directory
            zf.write(base / spec["sha256"], f"{pkg_name}/{spec['sha256']}")

            # Extra files (.h) inside package directory
            for extra in spec["extras"]:
                zf.write(base / extra, f"{pkg_name}/{extra}")

            # Python files
            pkg_dir = base / pkg_name
            for py_file in sorted(pkg_dir.glob("*.py")):
                zf.write(py_file, f"{pkg_name}/{py_file.name}")

    return zip_path


def print_zip_contents(zip_path):
    """Print zip file contents."""
    with zipfile.ZipFile(zip_path, "r") as zf:
        print(f"\n  {zip_path.name}:")
        for info in sorted(zf.infolist(), key=lambda i: i.filename):
            size = info.file_size
            if size > 1024 * 1024:
                s = f"{size / (1024 * 1024):.1f} MB"
            elif size > 1024:
                s = f"{size / 1024:.1f} KB"
            else:
                s = f"{size} B"
            print(f"    {info.filename:<55} {s:>10}")


def main():
    parser = argparse.ArgumentParser(description="Build vendor-pack zip files")
    parser.add_argument("version", help="Pack version (e.g. v1.0.0)")
    parser.add_argument("--dry-run", action="store_true", help="Validate only")
    args = parser.parse_args()

    version = args.version
    if not version.startswith("v"):
        print(f"Error: version must start with 'v' (got: {version})")
        sys.exit(1)

    print(f"Vendor pack {version}")
    print("=" * 50)

    # Validate
    for arch in ARCHITECTURES:
        print(f"\nValidating {arch}...")
        errors = validate_sources(arch)
        if errors:
            for e in errors:
                print(f"  ERROR: {e}")
            sys.exit(1)
        print("  OK")

    # Verify checksums
    for arch in ARCHITECTURES:
        print(f"Verifying checksums ({arch})...")
        errors = verify_checksums(arch)
        if errors:
            for e in errors:
                print(f"  ERROR: {e}")
            sys.exit(1)
        print("  OK")

    # Build
    if not args.dry_run and DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)

    for arch in ARCHITECTURES:
        print(f"\nBuilding {arch}...")
        zip_path = build_zip(version, arch, dry_run=args.dry_run)
        if not args.dry_run:
            print_zip_contents(zip_path)
            size_mb = zip_path.stat().st_size / (1024 * 1024)
            print(f"  Archive size: {size_mb:.1f} MB")

    print(f"\n{'=' * 50}")
    if args.dry_run:
        print("Dry run complete.")
    else:
        print(f"Output: {DIST_DIR}/")
        for f in sorted(DIST_DIR.iterdir()):
            print(f"  {f.name}")


if __name__ == "__main__":
    main()