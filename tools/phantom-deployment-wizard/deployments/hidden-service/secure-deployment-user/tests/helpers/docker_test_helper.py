"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Docker Test Helper for Secure Deployment User

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
"""

import time
import sys
import logging
import os
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

import docker
from docker.errors import ImageNotFound, ContainerError, BuildError, NotFound
from docker.models.containers import Container

# Docker Container Constants
DOCKER_IMAGE_NAME = "phantom-test-tools-systemd"
DOCKER_BUILD_TAG = "latest"
DOCKER_CONTAINER_PREFIX = "phantom-test-tools-systemd"
DOCKER_DOCKERFILE_NAME = "Dockerfile"

# Configure logging with explicit handler
# Check if we're running under pytest - pytest captures output differently than direct execution
in_pytest = "PYTEST_CURRENT_TEST" in os.environ

# Pytest detection is necessary because pytest intercepts stdout/stderr for test reporting
if in_pytest:
    # Simplified format for pytest test output (levelname only, no timestamps)
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s',  # Minimal format for cleaner test output
        handlers=[
            logging.StreamHandler(sys.stdout)
        ],
        force=True  # Override any existing logging configuration from pytest
    )
else:
    # Full format for standalone execution (includes timestamps and module names)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SystemdTestContainer:
    """Manages a Docker container running systemd for deployment-watcher testing."""

    def __init__(self, container_name: str = None):
        """Initializes systemd test container manager.
        Args:
            container_name: Optional custom container name. Defaults to process-specific name.
        """
        self.client = docker.from_env()
        self.container_name = container_name or f"{DOCKER_CONTAINER_PREFIX}-{os.getpid()}"
        self.container: Optional[Container] = None
        self.image_name = f"{DOCKER_IMAGE_NAME}:{DOCKER_BUILD_TAG}"
        self.dockerfile_name = DOCKER_DOCKERFILE_NAME

        # Directory mappings
        self.host_quarantine_dir: Optional[str] = None
        self.host_deployment_dir: Optional[str] = None
        self.host_secrets_dir: Optional[str] = None
        self.container_quarantine_dir: str = "/securepath/incoming"
        self.container_deployment_dir: str = "/tmp/deployment"
        self.container_secrets_dir: str = "/opt/deployment-secrets"

    def build_image(self, show_output: bool = True) -> None:
        """Builds the Docker image for systemd testing container.

        Args:
            show_output: Whether to display build output in real-time

        Raises:
            BuildError: If Docker image build fails
            ImageNotFound: If base image cannot be found
        """
        dockerfile_path = Path(__file__).parent.parent / self.dockerfile_name

        logger.info(f"Building Docker image from {dockerfile_path}")
        logger.info("=" * 60)

        try:
            # Check if image already exists
            try:
                self.client.images.get(self.image_name)
                logger.info(f"Image {self.image_name} already exists")
                logger.info(f"To rebuild, run: docker rmi {self.image_name}")
                logger.info("=" * 60)
                return
            except ImageNotFound:
                logger.info("Building new image...")

            # Build with streaming logs
            build_logs = self.client.api.build(
                path=str(dockerfile_path.parent),
                dockerfile=dockerfile_path.name,
                tag=self.image_name,
                rm=True,
                forcerm=True,
                decode=True
            )

            # Process and display build logs in real-time
            for log in build_logs:
                if 'stream' in log:
                    output = log['stream']
                    if show_output and output.strip():
                        # Use print for real-time output, logger buffers it
                        print(f"BUILD: {output.strip()}", flush=True)

                # Handle build steps
                elif 'status' in log:
                    status = log.get('status', '')
                    progress = log.get('progress', '')
                    if show_output and status:
                        logger.info(f"BUILD STATUS: {status} {progress}")

                # Handle aux messages (like image ID)
                elif 'aux' in log:
                    if 'ID' in log['aux']:
                        image_id = log['aux']['ID']
                        if show_output:
                            logger.info(f"Image ID: {image_id}")

                # Handle errors
                elif 'error' in log:
                    error_msg = log['error']
                    logger.error(f"BUILD ERROR: {error_msg}")
                    raise BuildError(error_msg, build_logs)

                # Handle error detail
                elif 'errorDetail' in log:
                    error_detail = log['errorDetail']
                    error_msg = error_detail.get('message', str(error_detail))
                    logger.error(f"BUILD ERROR: {error_msg}")
                    raise BuildError(error_msg, build_logs)

            logger.info("=" * 60)
            logger.info(f"Successfully built image: {self.image_name}")

        except BuildError as e:
            logger.error(f"Failed to build Docker image: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during Docker build: {e}")
            raise

    def start_container(self, show_output: bool = True) -> None:
        """Starts the Docker container with systemd support."""
        self.stop_container()

        if show_output:
            logger.info(f"Starting container: {self.container_name}")
            logger.info("=" * 60)

        try:
            # Create temp directories on host
            self.host_quarantine_dir = tempfile.mkdtemp(prefix="deployment_quarantine_")
            self.host_deployment_dir = tempfile.mkdtemp(prefix="deployment_test_")
            self.host_secrets_dir = tempfile.mkdtemp(prefix="deployment_secrets_")

            logger.info(f"Created host quarantine directory: {self.host_quarantine_dir}")
            logger.info(f"Created host deployment directory: {self.host_deployment_dir}")
            logger.info(f"Created host secrets directory: {self.host_secrets_dir}")

            # Define volumes
            volumes = {
                self.host_quarantine_dir: {
                    'bind': self.container_quarantine_dir,
                    'mode': 'rw'
                },
                self.host_deployment_dir: {
                    'bind': self.container_deployment_dir,
                    'mode': 'rw'
                },
                self.host_secrets_dir: {
                    'bind': self.container_secrets_dir,
                    'mode': 'rw'
                },
                '/sys/fs/cgroup': {
                    'bind': '/sys/fs/cgroup',
                    'mode': 'rw'
                }
            }

            if show_output:
                logger.info("Creating container with systemd support...")

            # Container configuration
            container_config = {
                'image': self.image_name,
                'name': self.container_name,
                'detach': True,
                'privileged': True,
                'cap_add': ["SYS_ADMIN"],
                'security_opt': ['seccomp=unconfined'],
                'volumes': volumes,
                'environment': {
                    "DEBIAN_FRONTEND": "noninteractive",
                    "container": "docker"
                },
                'remove': False,
                'tmpfs': {
                    '/run': 'rw,noexec,nosuid,size=256m',
                    '/run/lock': 'rw,noexec,nosuid,size=256m'
                },
                'cgroupns': 'host'
            }

            self.container = self.client.containers.run(**container_config)

            if show_output:
                logger.info(f"Container created: {self.container.short_id}")
                logger.info("Waiting for container to be ready...")

            # Wait for container
            self._wait_for_container(show_output=show_output)

            if show_output:
                logger.info("=" * 60)
                logger.info(f"Container {self.container_name} started successfully")

        except ContainerError as e:
            logger.error(f"Container failed to start: {e}")
            raise
        except ImageNotFound:
            logger.error(f"Image {self.image_name} not found. Run build_image() first.")
            raise

    def _wait_for_container(self, timeout: int = 30, show_output: bool = False) -> None:
        """Waits for container to be ready and optionally for systemd initialization.

        Polls container status until it responds to basic commands. If systemd is detected,
        waits additional time for service manager initialization before proceeding.

        Args:
            timeout: Maximum seconds to wait for container readiness
            show_output: Whether to log detailed status information

        Raises:
            RuntimeError: If container exits unexpectedly during startup
            TimeoutError: If container doesn't become ready within timeout period
        """
        start_time = time.time()
        systemd_wait_count = 0  # Counter to ensure systemd initialization completes before proceeding

        while time.time() - start_time < timeout:
            self.container.reload()

            if self.container.status == "running":
                # Check if we can execute basic commands
                result = self.exec_command("echo 'test'")
                if result['success']:
                    # Check if systemd is available (grep pattern ensures we find the actual systemd process, not just any process with 'systemd' in the name)
                    systemd_check = self.exec_command("ps aux | grep -E '^root.*systemd$' | grep -v grep || true")
                    if systemd_check['success'] and 'systemd' in systemd_check['output']:
                        # Systemd detected - increment counter to track initialization time
                        systemd_wait_count += 1
                        if systemd_wait_count >= 3:  # 3 iterations = 3 seconds wait for systemd services to initialize
                            if show_output:
                                logger.info("Container is ready (with systemd)")
                            logger.info("Container status: running, systemd detected")
                            return
                        else:
                            time.sleep(1)  # Sleep 1 second per iteration to give systemd time to start services
                            continue
                    else:
                        # No systemd, but container is ready
                        if show_output:
                            logger.info("Container is ready (without systemd)")
                        logger.info("Container status: running")
                        return

            elif self.container.status == "exited":
                # Container exited, get logs for debugging
                logs = self.get_container_logs(lines=20)
                logger.error(f"Container exited. Last logs:\n{logs}")
                raise RuntimeError(f"Container exited unexpectedly")

            time.sleep(1)

        # Container still not ready, get status info
        self.container.reload()
        logs = self.get_container_logs(lines=20)
        raise TimeoutError(
            f"Container not ready after {timeout} seconds. Status: {self.container.status}. Logs:\n{logs}")

    def exec_command(self, command: str) -> Dict[str, Any]:
        """Executes command inside Docker container and returns standardized result.

        Uses Docker exec_run with combined stdout/stderr output stream.

        Args:
            command: Shell command to execute in container

        Returns:
            Dictionary with standardized format:
                - exit_code: Command exit code (0 = success, -1 = exception)
                - output: Combined stdout/stderr as decoded UTF-8 string
                - error: Error message if exception occurred (otherwise empty)
                - success: Boolean indicating exit_code == 0
                - stdout: Alias for output (compatibility)
                - stderr: Empty string (combined with stdout in output)

        Raises:
            RuntimeError: If container is not running
        """
        if not self.container:
            raise RuntimeError("Container is not running")

        try:
            result = self.container.exec_run(
                command,
                stderr=True,
                stdout=True,
                demux=False  # Get combined output
            )

            # result.output is bytes when demux=False
            output = result.output.decode('utf-8') if result.output else ""

            return {
                'exit_code': result.exit_code,
                'output': output,
                'error': '',  # Combined in output
                'success': result.exit_code == 0,
                'stdout': output,  # For compatibility
                'stderr': ''  # Combined in output
            }

        except Exception as e:
            logger.error(f"Failed to execute command '{command}': {e}")
            return {
                'exit_code': -1,
                'output': '',
                'error': str(e),
                'success': False
            }

    def stop_container(self) -> None:
        """Stops and removes Docker container if it exists.

        Attempts graceful shutdown with 10-second timeout before forced removal.
        Silently succeeds if container doesn't exist (NotFound exception).
        """
        try:
            # Try to get existing container
            existing = self.client.containers.get(self.container_name)
            logger.info(f"Stopping existing container: {self.container_name}")
            existing.stop(timeout=10)
            existing.remove(force=True)
            logger.info(f"Removed container: {self.container_name}")
        except NotFound:
            pass  # Container doesn't exist
        except Exception as e:
            logger.warning(f"Error stopping container: {e}")

    def copy_file_to_container(self, host_path: Path, container_path: str) -> bool:
        """Copies a file from host to container using Docker API.

        Args:
            host_path: Path to file on host system
            container_path: Absolute path where file should be copied in container

        Returns:
            True if copy succeeded, False otherwise
        """
        if not self.container:
            raise RuntimeError("Container is not running")

        try:
            import tarfile
            import io

            # Create in-memory tar archive
            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode='w') as tar:
                # Add file to tar with target filename from container_path
                target_filename = Path(container_path).name
                tar.add(str(host_path), arcname=target_filename)

            tar_stream.seek(0)

            # Extract directory from container path
            container_dir = str(Path(container_path).parent)

            # Put archive into container
            success = self.container.put_archive(container_dir, tar_stream)

            if success:
                logger.info(f"✓ Copied {host_path.name} to {container_path}")
            else:
                logger.error(f"Failed to copy {host_path.name} to {container_path}")

            return success

        except Exception as e:
            logger.error(f"Error copying file to container: {e}")
            return False

    def get_container_logs(self, lines: int = 50) -> str:
        """Retrieves recent container logs with timestamps.

        Args:
            lines: Number of recent log lines to retrieve (default: 50)

        Returns:
            Decoded UTF-8 log output, or empty string if container not running or error occurs
        """
        if not self.container:
            return ""

        try:
            logs = self.container.logs(tail=lines, timestamps=True)
            return logs.decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to get container logs: {e}")
            return ""

    def cleanup(self) -> None:
        """Performs complete cleanup of container and host resources.

        Stops container and removes all temporary directories created during testing.
        Cleans up quarantine, deployment, and secrets directories from host filesystem.
        """
        self.stop_container()

        # Clean up host directories
        for dir_path in [self.host_quarantine_dir, self.host_deployment_dir, self.host_secrets_dir]:
            if dir_path and os.path.exists(dir_path):
                try:
                    shutil.rmtree(dir_path)
                    logger.info(f"Removed directory: {dir_path}")
                except Exception as e:
                    logger.error(f"Error cleaning up directory: {e}")

    def __enter__(self):
        """Context manager entry: builds image and starts container.

        Returns:
            Self for use in 'with' statement
        """
        self.build_image()
        self.start_container()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit: performs cleanup regardless of exceptions."""
        self.cleanup()


class DockerCommandExecutor:
    """
    Command executor that runs commands in Docker container.
    Implements the same interface as the regular run_command.
    """

    def __init__(self, container: SystemdTestContainer):
        """Initializes executor with systemd test container reference.

        Args:
            container: SystemdTestContainer instance to execute commands in
        """
        self.container = container

    def __call__(self, cmd) -> Dict[str, Any]:
        """Executes command in container (callable interface).

        Accepts both string and list command formats, converting lists to
        space-separated strings. Provides compatibility layer between Docker
        exec format and standard run_command interface.

        Args:
            cmd: Command as string or list of arguments

        Returns:
            Dictionary in run_command format:
                - success: Boolean indicating command success
                - stdout: Command output
                - stderr: Error output
                - returncode: Command exit code
        """
        # Convert list command to string
        if isinstance(cmd, list):
            command_str = ' '.join(cmd)
        else:
            command_str = str(cmd)  # Ensure it's a string

        # Execute in container
        result = self.container.exec_command(command_str)

        # Convert to run_command format
        return {
            'success': result['success'],
            'stdout': result['output'],
            'stderr': result['error'],
            'returncode': result['exit_code']
        }

    def run_command(self, cmd):
        """Executes command in container (method interface).

        Wrapper around __call__ for explicit method-style invocation.

        Args:
            cmd: Command as string or list of arguments

        Returns:
            Same as __call__: dictionary with success, stdout, stderr, returncode
        """
        return self.__call__(cmd)


def create_test_environment_with_docker():
    """
    Creates and initializes a complete Docker-based systemd test environment.

    Returns:
        Dict containing:
            - container: SystemdTestContainer instance
            - run_command: DockerCommandExecutor for running commands
            - host_quarantine_dir: Host directory for quarantine files
            - host_deployment_dir: Host directory for deployment files
            - host_secrets_dir: Host directory for secrets
    """
    container = SystemdTestContainer()
    container.build_image()
    container.start_container()

    executor = DockerCommandExecutor(container)

    return {
        'container': container,
        'run_command': executor,
        'host_quarantine_dir': container.host_quarantine_dir,
        'host_deployment_dir': container.host_deployment_dir,
        'host_secrets_dir': container.host_secrets_dir
    }
