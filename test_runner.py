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

Test runner for firewall-bridge v2.

Runs ALL tests (unit + integration) inside a Docker container and
produces a single combined coverage report.

Usage:
    python test_runner.py              # full run
    python test_runner.py --unit       # unit tests only
    python test_runner.py --integration # integration tests only
    python test_runner.py --no-build   # skip Docker image build
    python test_runner.py --force-build # force rebuild
"""

import argparse
import io
import logging
import os
import sys
import tarfile
import time
from datetime import datetime
from pathlib import Path

LOG_FMT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FMT,
                    handlers=[logging.StreamHandler(sys.stdout)])
log = logging.getLogger("test_runner")

ROOT = Path(__file__).parent
IMAGE_NAME = "firewall-bridge-v2-test:latest"
CONTAINER_PREFIX = "fw-bridge-test"


def step(msg: str):
    log.info(f"{'=' * 60}")
    log.info(f"STEP: {msg}")
    log.info(f"{'=' * 60}")


# ============================================================================
# Docker SDK
# ============================================================================

def get_docker_client():
    try:
        from docker import from_env
        from docker.errors import DockerException
    except ImportError:
        log.error("Docker SDK not installed (pip install docker)")
        return None
    try:
        client = from_env()
        client.ping()
        return client
    except DockerException as e:
        log.error(f"Docker not available: {e}")
        return None


def build_image(client, force: bool = False) -> bool:
    step("Building Docker image")
    from docker.errors import ImageNotFound

    if not force:
        try:
            client.images.get(IMAGE_NAME)
            log.info("Image exists (use --force-build to rebuild)")
            return True
        except ImageNotFound:
            pass

    try:
        for line in client.api.build(
            path=str(ROOT), dockerfile="tests/Dockerfile",
            tag=IMAGE_NAME, rm=True, forcerm=True, decode=True,
        ):
            if "stream" in line:
                text = line["stream"].strip()
                if text:
                    log.info(f"  BUILD | {text}")
            elif "error" in line:
                log.error(f"  BUILD ERROR | {line['error']}")
                return False
        log.info(f"Image built: {IMAGE_NAME}")
        return True
    except Exception as e:
        log.error(f"Build failed: {e}")
        return False


def start_container(client, name: str):
    step(f"Starting container: {name}")
    from docker.errors import NotFound, APIError
    try:
        old = client.containers.get(name)
        old.stop(timeout=3)
        old.remove(force=True)
    except (NotFound, APIError):
        pass

    container = client.containers.run(
        image=IMAGE_NAME, name=name, detach=True, privileged=True,
        cap_add=["NET_ADMIN", "SYS_ADMIN"],
        sysctls={"net.ipv4.ip_forward": "1"},
        remove=False,
    )
    for _ in range(30):
        container.reload()
        if container.status == "running":
            r = container.exec_run(["echo", "ready"])
            if r.exit_code == 0:
                log.info(f"Container ready: {name}")
                return container
        time.sleep(1)
    raise TimeoutError(f"Container {name} not ready")


def exec_in_container(container, cmd: str) -> tuple:
    """Execute command in container with real-time streaming output."""
    exec_id = container.client.api.exec_create(container.id, ["sh", "-c", cmd])
    stream = container.client.api.exec_start(exec_id, stream=True)

    lines = []
    for chunk in stream:
        text = chunk.decode("utf-8", errors="replace")
        for line in text.splitlines():
            lines.append(line)
            if line.strip():
                log.info(f"  TEST | {line}")

    inspect = container.client.api.exec_inspect(exec_id)
    exit_code = inspect.get("ExitCode", -1)
    return exit_code, "\n".join(lines)


def copy_from_container(container, src: str, dest: Path):
    from docker.errors import NotFound, APIError
    try:
        bits, _ = container.get_archive(src)
        tar_bytes = b"".join(bits)
        tf = tarfile.open(fileobj=io.BytesIO(tar_bytes))
        tf.extractall(path=str(dest))
        tf.close()
        return True
    except (NotFound, APIError, OSError):
        return False


def stop_container(container):
    from docker.errors import NotFound, APIError
    try:
        container.stop(timeout=5)
        container.remove(force=True)
    except (NotFound, APIError):
        pass


# ============================================================================
# Test execution
# ============================================================================

def run_tests(container, results_dir: Path, scope: str) -> tuple:
    """Run tests inside container with combined coverage."""
    unit_ok = True
    intg_ok = True

    if scope == "unit":
        test_paths = "tests/unit/"
        extra = ""
    elif scope == "integration":
        test_paths = "tests/integration/"
        extra = "--docker"
    else:
        test_paths = "tests/unit/ tests/integration/"
        extra = "--docker"

    step(f"Running tests: {scope}")

    cmd = (
        f"cd /workspace && python3 -m pytest {test_paths} {extra} "
        f"-v --tb=short "
        f"--cov=firewall_bridge --cov-report=term-missing "
        f"--cov-report=html:/workspace/coverage_html "
        f"2>&1"
    )

    exit_code, output = exec_in_container(container, cmd)

    log_path = results_dir / "tests.log"
    log_path.write_text(output)

    if "failed" in output.lower() or exit_code != 0:
        if scope in ("unit", "all"):
            if "tests/unit/" in output and "FAILED" in output:
                unit_ok = False
        if scope in ("integration", "all"):
            if "tests/integration/" in output and "FAILED" in output:
                intg_ok = False
        if exit_code != 0 and unit_ok and intg_ok:
            if scope == "unit":
                unit_ok = False
            elif scope == "integration":
                intg_ok = False
            else:
                intg_ok = False

    step("Collecting coverage report")
    if copy_from_container(container, "/workspace/coverage_html", results_dir):
        log.info(f"Coverage HTML → {results_dir / 'coverage_html'}")
    else:
        log.warning("Could not copy coverage HTML")

    return unit_ok, intg_ok


# ============================================================================
# Summary
# ============================================================================

def write_summary(results_dir: Path, unit_ok: bool, intg_ok: bool,
                  duration: float, scope: str):
    step("Test summary")
    overall = unit_ok and intg_ok

    lines = [
        "firewall-bridge v2 — Test Results",
        "=" * 50,
        f"Timestamp: {datetime.now().isoformat()}",
        f"Duration:  {duration:.1f}s",
        f"Scope:     {scope}",
        "",
        f"Unit tests:        {'PASSED' if unit_ok else 'FAILED'}",
        f"Integration tests: {'PASSED' if intg_ok else 'FAILED'}",
        f"Overall:           {'PASSED' if overall else 'FAILED'}",
        "",
        f"Results:  {results_dir}",
        f"Log:      {results_dir / 'tests.log'}",
        f"Coverage: {results_dir / 'coverage_html'}",
    ]
    (results_dir / "summary.txt").write_text("\n".join(lines) + "\n")
    for line in lines:
        log.info(f"  {line}")


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="firewall-bridge v2 test runner")
    parser.add_argument("--unit", action="store_true", help="Unit tests only")
    parser.add_argument("--integration", action="store_true",
                        help="Integration tests only")
    parser.add_argument("--no-build", action="store_true",
                        help="Skip Docker image build")
    parser.add_argument("--force-build", action="store_true",
                        help="Force image rebuild")
    args = parser.parse_args()

    scope = "all"
    if args.unit:
        scope = "unit"
    elif args.integration:
        scope = "integration"

    start_time = time.time()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = ROOT / "test_results" / timestamp
    results_dir.mkdir(parents=True, exist_ok=True)
    log.info(f"Results → {results_dir}")

    client = get_docker_client()
    if client is None:
        log.error("Docker required")
        sys.exit(1)

    if not args.no_build:
        if not build_image(client, force=args.force_build):
            sys.exit(1)

    name = f"{CONTAINER_PREFIX}-{os.getpid()}"
    container = start_container(client, name)

    try:
        unit_ok, intg_ok = run_tests(container, results_dir, scope)
    finally:
        stop_container(container)
        log.info(f"Container {name} destroyed")

    duration = time.time() - start_time
    write_summary(results_dir, unit_ok, intg_ok, duration, scope)

    overall = unit_ok and intg_ok
    step(f"OVERALL: {'PASSED' if overall else 'FAILED'} ({duration:.1f}s)")
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()