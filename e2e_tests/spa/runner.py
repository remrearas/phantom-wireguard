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
WireGuard® is a registered trademark of Jason A. Donenfeld.

SPA E2E test runner — host-side orchestration via compose-bridge.

Bootstraps isolated secrets/DB, builds the SPA, starts the full topology
(daemon, auth-service, nginx, playwright), runs Playwright inside the
playwright container, then tears down.

Videos and HTML report are written to mounted volumes (results/, report/).

Usage:
    ./tools/dev.sh test-spa-e2e
    ./tools/dev.sh test-spa-e2e --no-cleanup
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import time
from pathlib import Path

RUNNER_DIR = Path(__file__).parent
E2E_DIR = RUNNER_DIR.parent
REPO_ROOT = E2E_DIR.parent
sys.path.insert(0, str(REPO_ROOT))

from e2e_tests.environment import E2ETestEnvironment, step, LOG_FMT

logging.basicConfig(
    level=logging.INFO, format=LOG_FMT,
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("e2e.spa")

COMPOSE_PATH = str(RUNNER_DIR / "docker-compose.yml")
SPA_DIR = REPO_ROOT / "services" / "react-spa"
BOOTSTRAP_SCRIPT = RUNNER_DIR / "helpers" / "bootstrap.sh"
SECRETS_DIR = RUNNER_DIR / "container-data" / "secrets"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SPA E2E test runner")
    parser.add_argument(
        "--no-cleanup", action="store_true",
        help="Keep containers after tests (for debugging)",
    )
    parser.add_argument(
        "--wg-clients", type=int, default=1, metavar="N",
        help="Number of wg-client replicas (default: 1)",
    )
    parser.add_argument(
        "playwright_args", nargs="*",
        help="Extra arguments passed to Playwright (e.g. --grep 'login')",
    )
    return parser.parse_args()


def bootstrap() -> None:
    """Generate isolated secrets, TLS cert, and auth DB."""
    step("Bootstrapping secrets and auth DB")
    subprocess.run(
        ["bash", str(BOOTSTRAP_SCRIPT)],
        cwd=str(REPO_ROOT),
        check=True,
    )


def build_spa() -> None:
    """Build the React SPA so nginx can serve dist/."""
    step("Building SPA")
    subprocess.run(
        ["npm", "run", "build"],
        cwd=str(SPA_DIR),
        check=True,
    )


def read_secret(name: str) -> str:
    """Read a secret value from the spa container-data secrets."""
    return (SECRETS_DIR / name).read_text().strip()


def main() -> None:
    args = parse_args()
    start_time = time.time()
    rc = 1

    wg_count = args.wg_clients
    env = E2ETestEnvironment("spa", compose_path=COMPOSE_PATH)

    try:
        # Fresh secrets + DB every run
        bootstrap()

        # Build SPA before starting compose (nginx needs dist/)
        build_spa()

        env.up()

        # Scale wg-client replicas if requested (bridge ignores deploy.replicas)
        if wg_count > 1:
            step(f"Scaling wg-client to {wg_count} replicas")
            subprocess.run(
                [
                    "docker", "compose",
                    "-f", COMPOSE_PATH,
                    "-p", env.project_name,
                    "up", "-d", "--scale", f"wg-client={wg_count}",
                    "--no-recreate", "wg-client",
                ],
                check=True,
            )

        # Wait for backend services
        env.wait_for_log("daemon", "Application startup complete", timeout=60)
        env.wait_for_log("auth-service", "Application startup complete", timeout=60)

        # Wait for playwright container
        env.wait_for_ready("playwright", timeout=30)

        # Read admin password for test env
        admin_password = read_secret(".admin_password")

        # Run Playwright inside the container (streaming via subprocess)
        step("Running Playwright tests")
        pw_cmd = ["npx", "playwright", "test"]
        if args.playwright_args:
            pw_cmd.extend(args.playwright_args)

        docker_cmd = [
            "docker", "compose",
            "-f", COMPOSE_PATH,
            "-p", env.project_name,
            "exec",
            "-e", f"ADMIN_PASSWORD={admin_password}",
            "-e", f"COMPOSE_PROJECT_NAME={env.project_name}",
            "-e", f"WG_CLIENT_COUNT={wg_count}",
            "-T", "playwright",
            *pw_cmd,
        ]

        proc = subprocess.Popen(
            docker_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
        )
        for raw in proc.stdout:
            line = raw.decode("utf-8", errors="replace").rstrip("\n")
            sys.stdout.write(f"  PW | {line}\n")
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