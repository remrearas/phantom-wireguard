#!/usr/bin/env python3
"""
Firewall Bridge — Unit Test Runner

Builds the test image, runs pytest with coverage, streams output.

Usage:
    python tests/runner.py
"""

import sys
import time
from pathlib import Path

import docker
from docker.errors import BuildError, ImageNotFound, NotFound

IMAGE = "firewall-bridge-unit:latest"
CONTAINER = "fw-unit-test"
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)


def main() -> None:
    start = time.time()
    client = docker.from_env()

    print("=" * 60)
    print("BUILD")
    print("=" * 60)

    try:
        for line in client.api.build(
            path=PROJECT_ROOT, dockerfile="tests/Dockerfile",
            tag=IMAGE, rm=True, forcerm=True, decode=True,
        ):
            if "stream" in line:
                print(line["stream"], end="", flush=True)
            elif "error" in line:
                print(f"ERROR: {line['error']}", flush=True)
                sys.exit(1)
    except BuildError as e:
        print(f"BUILD FAILED: {e}")
        sys.exit(1)

    # Verify image exists
    try:
        client.images.get(IMAGE)
    except ImageNotFound:
        print(f"Image not found after build: {IMAGE}")
        sys.exit(1)

    print("=" * 60)
    print("TEST")
    print("=" * 60)

    try:
        old = client.containers.get(CONTAINER)
        old.remove(force=True)
    except NotFound:
        pass

    container = client.containers.run(
        IMAGE, name=CONTAINER, detach=True,
        privileged=True, cap_add=["NET_ADMIN"],
    )

    try:
        for chunk in container.logs(stream=True, follow=True):
            print(chunk.decode("utf-8", errors="replace"), end="", flush=True)

        container.reload()
        rc = container.attrs["State"]["ExitCode"]
    finally:
        container.remove(force=True)

    duration = time.time() - start
    status = "PASSED" if rc == 0 else "FAILED"

    print("=" * 60)
    print(f"RESULT: {status} ({duration:.1f}s)")
    print("=" * 60)

    client.close()
    sys.exit(rc)


if __name__ == "__main__":
    main()
