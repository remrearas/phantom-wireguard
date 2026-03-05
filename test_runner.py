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

Test runner for compose-bridge v1.0.0.

Uses the compose bridge itself to validate all FFI operations:
    load → up → ps → exec → logs → down

Usage:
    python test_runner.py            # full run
    python test_runner.py --build    # build .so/.dylib first, then test
"""

from __future__ import annotations

import argparse
import logging
import os
import platform
import subprocess
import sys
from pathlib import Path

LOG_FMT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FMT,
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("test_runner")

ROOT = Path(__file__).parent
COMPOSE_FILE = str(ROOT / "tests" / "docker-compose-test.yml")
PROJECT_NAME = "cb-test"


def step(msg: str):
    log.info("=" * 60)
    log.info("STEP: %s", msg)
    log.info("=" * 60)


# ============================================================================
# Build
# ============================================================================


def build_library() -> bool:
    """Build the shared library for the current platform."""
    system = platform.system().lower()
    arch = platform.machine()
    go_arch = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "amd64"}.get(
        arch, arch
    )
    target = f"build-{system}-{go_arch}"

    step(f"Building compose_bridge ({target})")
    result = subprocess.run(
        ["make", target],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        log.error("Build failed:\n%s", result.stderr)
        return False
    log.info("Build OK")
    return True


# ============================================================================
# Tests
# ============================================================================


def run_tests() -> bool:
    """Run the compose bridge integration tests."""
    from compose_bridge import ComposeBridge, ExecResult

    passed = 0
    failed = 0

    def check(name: str, condition: bool, detail: str = ""):
        nonlocal passed, failed
        if condition:
            log.info("  PASS: %s", name)
            passed += 1
        else:
            log.error("  FAIL: %s %s", name, detail)
            failed += 1

    # --- Version ---
    step("Version check")
    with ComposeBridge(COMPOSE_FILE, project_name="cb-ver") as b:
        ver = b.version()
        check("version == 1.0.0", ver == "1.0.0", f"got {ver!r}")

    # --- Lifecycle ---
    step("Project lifecycle: load → up → ps → exec → logs → down")
    with ComposeBridge(COMPOSE_FILE, project_name=PROJECT_NAME) as bridge:

        # up
        step("up")
        bridge.up()
        log.info("  Services started")

        # ps
        step("ps")
        containers = bridge.ps()
        check("ps returns list", isinstance(containers, list))
        check("ps has containers", len(containers) >= 1)
        check(
            "alpine service found",
            any(c["service"] == "alpine" for c in containers),
            f"got {[c['service'] for c in containers]}",
        )
        for c in containers:
            log.info(
                "  Container: %s  service=%s  state=%s",
                c.get("name", "?"),
                c.get("service", "?"),
                c.get("state", "?"),
            )

        # exec: echo
        step("exec echo")
        result = bridge.exec("alpine", ["echo", "hello"])
        check("exec returns ExecResult", isinstance(result, ExecResult))
        check("exit_code == 0", result.exit_code == 0, f"got {result.exit_code}")
        check("stdout contains hello", "hello" in result.stdout, f"got {result.stdout!r}")

        # exec: env
        step("exec with env")
        result = bridge.exec(
            "alpine",
            ["sh", "-c", "echo $MY_VAR"],
            env={"MY_VAR": "phantom"},
        )
        check("env exit_code == 0", result.exit_code == 0)
        check("env stdout contains phantom", "phantom" in result.stdout)

        # exec: nonzero exit
        step("exec nonzero exit")
        result = bridge.exec("alpine", ["sh", "-c", "exit 42"])
        check("nonzero exit_code == 42", result.exit_code == 42, f"got {result.exit_code}")

        # logs
        step("logs")
        logs = bridge.logs("alpine")
        check("logs returns str", isinstance(logs, str))

        # down
        step("down")
        bridge.down()
        log.info("  Services stopped")

    # --- Summary ---
    total = passed + failed
    log.info("=" * 60)
    log.info("RESULTS: %d/%d passed, %d failed", passed, total, failed)
    log.info("=" * 60)

    return failed == 0


# ============================================================================
# Main
# ============================================================================


def main():
    parser = argparse.ArgumentParser(description="compose-bridge test runner")
    parser.add_argument(
        "--build", action="store_true", help="build library before testing"
    )
    args = parser.parse_args()

    if args.build:
        if not build_library():
            sys.exit(1)

    step("Running compose-bridge tests")
    ok = run_tests()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
