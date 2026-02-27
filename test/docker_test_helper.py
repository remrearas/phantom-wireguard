"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""
"""
Docker Test Helper for wireguard-go-bridge integration tests.

Manages the lifecycle of a privileged Docker container that:
1. Builds wireguard_go_bridge.so from Go source inside the container (multi-stage)
2. Runs the Python FFI bridge for WireGuard interface creation
3. Provides network namespace and TUN device support for real tunnel tests

Pattern adapted from phantom/modules/core/tests/helpers/docker_test_helper.py
"""

import os
import sys
import time
import logging
from typing import Optional, Dict, Any

import docker
from docker.errors import ImageNotFound, BuildError
from docker.models.containers import Container

DOCKER_IMAGE_NAME = "wireguard-go-bridge-test"
DOCKER_BUILD_TAG = "latest"
DOCKER_CONTAINER_PREFIX = "wg-bridge-test"
DOCKER_DOCKERFILE_NAME = "Dockerfile"

in_pytest = "PYTEST_CURRENT_TEST" in os.environ

if in_pytest:
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
else:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)],
    )

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class BridgeTestContainer:
    """
    Manages a Docker container for wireguard-go-bridge integration testing.

    The container:
    - Builds the Go bridge from source (multi-stage Dockerfile)
    - Has wireguard-tools, iproute2, iptables for real WireGuard testing
    - Runs privileged with NET_ADMIN and TUN device access
    - Supports network namespace creation for tunnel tests
    """

    def __init__(self, container_name: Optional[str] = None):
        self.client = docker.from_env()
        self.container_name = container_name or f"{DOCKER_CONTAINER_PREFIX}-{os.getpid()}"
        self.container: Optional[Container] = None
        self.image_name = f"{DOCKER_IMAGE_NAME}:{DOCKER_BUILD_TAG}"

    def build_image(self, show_output: bool = True) -> None:
        """Build Docker image with Go compilation and test environment.

        Uses multi-stage build: Go builder compiles wireguard_go_bridge.so,
        then Debian slim image gets the binary + Python package + test files.

        Build output is streamed to stdout in real-time.
        """
        test_dir = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.dirname(test_dir)

        logger.info(f"Building Docker image: {self.image_name}")
        logger.info(f"Build context: {repo_root}")
        logger.info("=" * 60)

        try:
            try:
                self.client.images.get(self.image_name)
                logger.info(f"Image {self.image_name} already exists")
                logger.info(f"To rebuild, run: docker rmi {self.image_name}")
                logger.info("=" * 60)
                return
            except ImageNotFound:
                logger.info("Building new image (includes Go compilation)...")

            build_logs = self.client.api.build(
                path=repo_root,
                dockerfile="test/Dockerfile",
                tag=self.image_name,
                rm=True,
                forcerm=True,
                decode=True,
            )

            for log in build_logs:
                if "stream" in log:
                    output = log["stream"]
                    if show_output and output.strip():
                        print(f"BUILD: {output.strip()}", flush=True)

                elif "status" in log:
                    status = log.get("status", "")
                    progress = log.get("progress", "")
                    if show_output and status:
                        logger.info(f"BUILD STATUS: {status} {progress}")

                elif "aux" in log:
                    if "ID" in log["aux"]:
                        image_id = log["aux"]["ID"]
                        if show_output:
                            logger.info(f"Image ID: {image_id}")

                elif "error" in log:
                    error_msg = log["error"]
                    logger.error(f"BUILD ERROR: {error_msg}")
                    raise BuildError(error_msg, build_logs)

                elif "errorDetail" in log:
                    error_detail = log["errorDetail"]
                    error_msg = error_detail.get("message", str(error_detail))
                    logger.error(f"BUILD ERROR: {error_msg}")
                    raise BuildError(error_msg, build_logs)

            logger.info("=" * 60)
            logger.info(f"Successfully built image: {self.image_name}")

        except BuildError:
            raise
        except ImageNotFound as e:
            logger.error(f"Base image not found: {e}")
            raise

    def start_container(self, show_output: bool = True) -> None:
        """Start privileged container with TUN and network namespace support."""
        self.stop_container()

        if show_output:
            logger.info(f"Starting container: {self.container_name}")
            logger.info("=" * 60)

        self.container = self.client.containers.run(
            image=self.image_name,
            name=self.container_name,
            detach=True,
            privileged=True,
            cap_add=["NET_ADMIN", "SYS_ADMIN"],
            devices=["/dev/net/tun:/dev/net/tun"],
            sysctls={
                "net.ipv4.ip_forward": "1",
                "net.ipv6.conf.all.forwarding": "1",
            },
            volumes={
                "/lib/modules": {"bind": "/lib/modules", "mode": "ro"},
            },
            remove=False,
        )

        self._wait_for_container(show_output=show_output)

        if show_output:
            logger.info("=" * 60)
            logger.info(f"Container {self.container_name} ready")

    def _wait_for_container(self, timeout: int = 30, show_output: bool = False) -> None:
        """Wait until container is responsive."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            self.container.reload()

            if self.container.status == "running":
                result = self.exec_command("echo ready")
                if result["success"]:
                    if show_output:
                        logger.info("Container is ready")
                    return

            elif self.container.status == "exited":
                logs = self.get_container_logs(lines=20)
                logger.error(f"Container exited. Last logs:\n{logs}")
                raise RuntimeError("Container exited unexpectedly")

            time.sleep(1)

        self.container.reload()
        logs = self.get_container_logs(lines=20)
        raise TimeoutError(
            f"Container not ready after {timeout}s. "
            f"Status: {self.container.status}. Logs:\n{logs}"
        )

    def exec_command(self, command: str) -> Dict[str, Any]:
        """Execute command in container with standardized result format."""
        if not self.container:
            raise RuntimeError("Container not started")

        exit_code, output = self.container.exec_run(
            ["sh", "-c", command],
            demux=False,
        )

        stdout = output.decode("utf-8", errors="replace") if output else ""

        return {
            "exit_code": exit_code,
            "output": stdout,
            "success": exit_code == 0,
            "stdout": stdout,
            "stderr": "",
        }

    def run_test_sh(self) -> Dict[str, Any]:
        """Run the main netns integration test script with streaming output."""
        if not self.container:
            raise RuntimeError("Container not started")

        cmd = "stdbuf -oL -eL ./test/test.sh /workspace/wireguard_go_bridge.so 2>&1"

        exec_id = self.client.api.exec_create(
            self.container.id,
            ["sh", "-c", f"cd /workspace && {cmd}"],
            stdout=True,
            stderr=True,
        )

        output_lines = []
        stream = self.client.api.exec_start(exec_id, stream=True)
        for chunk in stream:
            text = chunk.decode("utf-8", errors="replace")
            for line in text.splitlines():
                if line:
                    logger.info(line)
                    output_lines.append(line)

        inspect = self.client.api.exec_inspect(exec_id)
        exit_code = inspect.get("ExitCode", -1)

        full_output = "\n".join(output_lines)
        return {
            "exit_code": exit_code,
            "output": full_output,
            "success": exit_code == 0,
            "stdout": full_output,
            "stderr": "",
        }

    def get_container_logs(self, lines: int = 50) -> str:
        """Retrieve recent container logs for debugging."""
        if not self.container:
            return ""
        try:
            logs = self.container.logs(tail=lines)
            return logs.decode("utf-8", errors="replace") if logs else ""
        except (docker.errors.APIError, docker.errors.NotFound):
            return ""

    def stop_container(self) -> None:
        """Stop and remove container gracefully."""
        if self.container:
            try:
                self.container.stop(timeout=5)
                self.container.remove(force=True)
            except (docker.errors.APIError, docker.errors.NotFound):
                pass
            self.container = None

        # Also clean up any stale container with our name
        try:
            stale = self.client.containers.get(self.container_name)
            stale.stop(timeout=5)
            stale.remove(force=True)
        except (docker.errors.APIError, docker.errors.NotFound):
            pass

    def cleanup(self) -> None:
        """Full cleanup: stop container."""
        self.stop_container()

    def __enter__(self):
        self.build_image()
        self.start_container()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()