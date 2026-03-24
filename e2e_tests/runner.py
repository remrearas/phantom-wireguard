#!/usr/bin/env python3
"""
Firewall Bridge E2E test runner — host-side orchestration via compose-bridge.

Starts the full topology (bridge, exit-server, client),
runs pytest inside the bridge container, then tears down.

Usage:
    python e2e_tests/runner.py
    python e2e_tests/runner.py --no-cleanup
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import time
from pathlib import Path

RUNNER_DIR = Path(__file__).parent
PROJECT_ROOT = RUNNER_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from e2e_tests.environment import E2ETestEnvironment, step, LOG_FMT

logging.basicConfig(
    level=logging.INFO, format=LOG_FMT,
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("e2e.firewall-bridge")

COMPOSE_PATH = str(RUNNER_DIR / "docker-compose.yml")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Firewall Bridge E2E test runner")
    parser.add_argument(
        "--no-cleanup", action="store_true",
        help="Keep containers after tests (for debugging)",
    )
    parser.add_argument(
        "pytest_args", nargs="*",
        help="Extra arguments passed to pytest",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    start_time = time.time()
    rc = 1

    env = E2ETestEnvironment("fw", compose_path=COMPOSE_PATH)

    try:
        env.up()

        env.wait_for_log("exit-server", "EXIT_READY", timeout=30)
        env.wait_for_ready("bridge", timeout=30)

        step("Running E2E tests in bridge container")
        pytest_cmd = [
            "python3", "-m", "pytest",
            "e2e_tests/tests/",
            "-v", "-s",
        ]
        if args.pytest_args:
            pytest_cmd.extend(args.pytest_args)

        docker_cmd = [
            "docker", "compose",
            "-f", COMPOSE_PATH,
            "-p", env.project_name,
            "exec",
            "-e", f"COMPOSE_PROJECT_NAME={env.project_name}",
            "-T", "bridge",
            *pytest_cmd,
        ]

        proc = subprocess.Popen(
            docker_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
        )
        for raw in proc.stdout:
            line = raw.decode("utf-8", errors="replace").rstrip("\n")
            sys.stdout.write(f"  TEST | {line}\n")
            sys.stdout.flush()
        rc = proc.wait()

    except Exception as exc:
        log.error("E2E FAILED: %s", exc)
        rc = 1

    finally:
        duration = time.time() - start_time
        status = "PASSED" if rc == 0 else "FAILED"
        step(f"RESULT: {status} ({duration:.1f}s)")

        if not args.no_cleanup:
            env.close()
        else:
            log.info("Skipping cleanup (--no-cleanup)")

    sys.exit(rc)


if __name__ == "__main__":
    main()
