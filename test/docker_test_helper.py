"""
Docker Test Helper for wstunnel-bridge integration tests.

Manages the lifecycle of a Docker container that:
1. Runs wstunnel server for WebSocket tunnel testing
2. Loads libwstunnel_bridge_linux.so via Python FFI
3. Provides echo servers for UDP/TCP tunnel verification

Pattern adapted from dev/wireguard-go-bridge test/docker_test_helper.py
"""

import os
import sys
import time
import logging
from typing import Optional, Dict, Any

import docker
from docker.errors import ImageNotFound, BuildError
from docker.models.containers import Container

DOCKER_IMAGE_NAME = "wstunnel-bridge-test"
DOCKER_BUILD_TAG = "latest"
DOCKER_CONTAINER_PREFIX = "ws-bridge-test"

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


class WstunnelTestContainer:
    """
    Manages a Docker container for wstunnel-bridge integration testing.

    The container:
    - Has wstunnel server binary for WebSocket tunnel endpoint
    - Has libwstunnel_bridge_linux.so for FFI bridge testing
    - Has socat/ncat for echo servers
    - Does NOT require privileged mode (no TUN/netns needed)
    """

    def __init__(self, container_name: Optional[str] = None):
        self.client = docker.from_env()
        self.container_name = container_name or f"{DOCKER_CONTAINER_PREFIX}-{os.getpid()}"
        self.container: Optional[Container] = None
        self.image_name = f"{DOCKER_IMAGE_NAME}:{DOCKER_BUILD_TAG}"

    def build_image(self, show_output: bool = True) -> None:
        """Build Docker image with wstunnel server and test dependencies."""
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
                logger.info("Building new image...")

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
        """Start container with wstunnel server."""
        self.stop_container()

        if show_output:
            logger.info(f"Starting container: {self.container_name}")
            logger.info("=" * 60)

        self.container = self.client.containers.run(
            image=self.image_name,
            name=self.container_name,
            detach=True,
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
