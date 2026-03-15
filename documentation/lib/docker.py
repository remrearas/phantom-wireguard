"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Phantom Documentation Kit - Docker Integration
Docker SDK implementation for containerized builds and serving
"""

from pathlib import Path
from typing import Dict, Optional, Any
import os
import subprocess
import time
import threading
import re
from datetime import datetime
import docker
from docker.models.images import Image
from docker.errors import DockerException, BuildError, APIError, NotFound

from .logging import get_logger

class DockerManager:
    """Handles Docker container lifecycle and operations"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.docker_config = config.get('docker', {
            'image_name': 'phantom-docs-kit',
            'build_tag': 'latest',
            'container_prefix': 'phantom-docs'
        })
        self.client = None
        self.container = None
        self._cleanup_performed = False
        
    def connect(self) -> bool:
        """Connect to Docker daemon"""
        logger = get_logger(__name__)
        try:
            self.client = docker.from_env()
            # Test connection
            self.client.ping()
            logger.info("Connected to Docker daemon")
            return True
        except DockerException as e:
            logger.error(f"Failed to connect to Docker: {e}")
            logger.error("Please ensure Docker is installed and running.")
            return False
            
    def ensure_image(self, dockerfile_path: str = '.Dockerfile') -> Optional[Image]:
        """Build Docker image if not exists"""
        logger = get_logger(__name__)
        if not self.client:
            return None
            
        image_tag = f"{self.docker_config['image_name']}:{self.docker_config['build_tag']}"
        
        try:
            # Check if image exists
            try:
                image = self.client.images.get(image_tag)
                logger.info(f"Docker image '{image_tag}' found")
                return image
            except docker.errors.ImageNotFound:
                logger.info(f"Building Docker image '{image_tag}'...")
                
            # Build image
            dockerfile = Path(dockerfile_path)
            if not dockerfile.exists():
                logger.error(f"Dockerfile not found at {dockerfile_path}")
                return None
                
            logger.info("Starting Docker build process...")
            logger.info(f"Building from: {dockerfile_path}")
            logger.info(f"Context: {Path('.').resolve()}")
            
            # Build with real-time output
            try:
                # Use low-level API for better control
                build_stream = self.client.api.build(
                    path=".",
                    dockerfile=dockerfile_path,
                    tag=image_tag,
                    rm=True,
                    forcerm=True,
                    decode=True  # Decode JSON responses
                )
                
                # Process build output
                for chunk in build_stream:
                    if 'stream' in chunk:
                        # For build output, we still print directly to maintain real-time feedback
                        print(chunk['stream'], end='', flush=True)
                    elif 'error' in chunk:
                        logger.error(chunk['error'])
                        return None
                    elif 'aux' in chunk:
                        # This contains the image ID when build is complete
                        if 'ID' in chunk['aux']:
                            logger.info("\nDocker image built successfully")
                            logger.info(f"Image ID: {chunk['aux']['ID']}")
                
                # Get the image object
                image = self.client.images.get(image_tag)
                return image
                
            except Exception as e:
                logger.error(f"Build error: {e}", exc_info=True)
                return None
            
        except BuildError as e:
            logger.error(f"Docker build failed: {e}")
            for log in e.build_log:
                if 'stream' in log:
                    logger.error(log['stream'].strip())
            return None
        except APIError as e:
            logger.error(f"Docker API error: {e}")
            return None
    
    # noinspection PyMethodMayBeStatic
    def detect_docker_environment(self) -> Dict[str, Any]:
        """Detect Docker environment and capabilities"""
        logger = get_logger(__name__)
        docker_host = os.environ.get('DOCKER_HOST', '')
        is_remote = bool(docker_host and not docker_host.startswith('unix://'))
        
        # Only check Mutagen if remote Docker is detected
        mutagen_available = False
        mutagen_version = None
        
        if is_remote:
            from .main import check_mutagen
            mutagen_available = check_mutagen()
            
            if not mutagen_available:
                logger.error("Remote Docker detected but Mutagen not installed")
                logger.error("Mutagen is REQUIRED for remote Docker synchronization")
                logger.error("Install Mutagen:")
                logger.error("  macOS: brew install mutagen-io/mutagen/mutagen")
                logger.error("  Linux: Download from https://github.com/mutagen-io/mutagen/releases")
                logger.error("  Download from https://github.com/mutagen-io/mutagen/releases")
                raise RuntimeError("Mutagen is required for remote Docker")
            
            # Get version if available
            result = subprocess.run(['mutagen', 'version'], capture_output=True, text=True)
            if result.returncode == 0:
                mutagen_version = result.stdout.strip()
        
        return {
            'is_remote': is_remote,
            'docker_host': docker_host,
            'mutagen_available': mutagen_available,
            'mutagen_version': mutagen_version,
            'sync_strategy': 'mutagen' if is_remote else 'volumes'
        }
    
    # noinspection PyMethodMayBeStatic
    def _prepare_volumes(self, working_path: Path) -> Dict:
        """Prepare volume mappings for Docker container
        
        Args:
            working_path: Resolved path to working directory
            
        Returns:
            Dictionary of volume mappings
        """
        volumes = {}
        
        # Mount everything except tools directory
        for item in working_path.iterdir():
            if item.is_dir() and item.name != "tools":
                volumes[str(item)] = {"bind": f"/app/{item.name}", "mode": "rw"}
            elif item.is_file():
                volumes[str(item)] = {"bind": f"/app/{item.name}", "mode": "ro"}
        
        # Mount tools directory but exclude vendor-builder and image-optimizer
        tools_path = working_path / "tools"
        if tools_path.exists():
            for item in tools_path.iterdir():
                if item.is_dir() and item.name not in ["vendor-builder", "image-optimizer"]:
                    volumes[str(item)] = {"bind": f"/app/tools/{item.name}", "mode": "rw"}
        
        # Mount Node.js tool directories with proper exclusions
        node_tools = ["vendor-builder", "image-optimizer"]
        for tool_name in node_tools:
            tool_path = working_path / "tools" / tool_name
            if tool_path.exists():
                self._mount_node_tool(tool_path, f"/app/tools/{tool_name}", volumes)
        
        return volumes
    
    # noinspection PyMethodMayBeStatic
    def _mount_node_tool(self, tool_path: Path, mount_path: str, volumes: Dict) -> None:
        """Mount Node.js tool directory with proper exclusions
        
        Args:
            tool_path: Path to the tool directory
            mount_path: Mount path in the container
            volumes: Volume mappings dictionary to update
        """
        # Define files/directories to exclude
        exclude_items = {
            "node_modules",      # NPM dependencies
            "package-lock.json", # NPM lock file
            ".npm",             # NPM cache
            ".cache",           # Generic cache
            ".DS_Store",        # macOS metadata
        }
        
        for item in tool_path.iterdir():
            # Skip excluded items
            if item.name in exclude_items:
                continue
            if item.is_file():
                if item.suffix in ['.js', '.json']:
                    volumes[str(item)] = {"bind": f"{mount_path}/{item.name}", "mode": "rw"}
                else:
                    volumes[str(item)] = {"bind": f"{mount_path}/{item.name}", "mode": "ro"}
            elif item.is_dir():
                volumes[str(item)] = {"bind": f"{mount_path}/{item.name}", "mode": "rw"}
            
    def run_build(self, working_dir: str = ".") -> bool:
        """Run build in Docker container with hot reload"""
        logger = get_logger(__name__)
        
        # Detect environment and choose strategy
        env = self.detect_docker_environment()
        
        if env['sync_strategy'] == 'volumes':
            # Existing local Docker implementation
            return self._run_build_with_volumes(working_dir)
        elif env['sync_strategy'] == 'mutagen':
            logger.info("Remote Docker detected - using Mutagen synchronization")
            logger.info(f"Mutagen version: {env['mutagen_version']}")
            return self._run_build_with_mutagen(working_dir)
        else:
            logger.error("Remote Docker detected but Mutagen not installed")
            logger.error("Please install Mutagen to enable file synchronization")
            logger.error("  macOS: brew install mutagen-io/mutagen/mutagen")
            logger.error("  Linux: Download from https://github.com/mutagen-io/mutagen/releases")
            return False
    
    def _run_build_with_volumes(self, working_dir: str = ".") -> bool:
        """Original run_build implementation with volume mappings"""
        logger = get_logger(__name__)
        if not self.client:
            return False
            
        container_name = f"{self.docker_config['container_prefix']}-build"
        image_tag = f"{self.docker_config['image_name']}:{self.docker_config['build_tag']}"
        
        # Prepare volumes
        working_path = Path(working_dir).resolve()
        volumes = self._prepare_volumes(working_path)
        
        try:
            # Remove existing container if any
            self._remove_existing_container(container_name, force=True)
                
            logger.info("Running build in Docker container...")
            
            # Run container
            container = self.client.containers.run(
                image=image_tag,
                name=container_name,
                volumes=volumes,
                command=["python", "build.py"],
                detach=True,
                remove=False,
                working_dir="/app",
                environment={
                    "PYTHONUNBUFFERED": "1",  # For real-time log output
                    "DOCKER_MODE": "1"  # Flag to indicate Docker mode
                }
            )
            
            # Stream logs
            for log in container.logs(stream=True):
                # Decode and process log line
                log_line = log.decode('utf-8').rstrip()
                if log_line:
                    # Route container logs through our logger
                    logger.info(log_line)
                
            # Wait for completion
            result = container.wait()
            exit_code = result['StatusCode']
            
            # Clean up
            container.remove()
            
            if exit_code == 0:
                logger.info("Docker build completed successfully")
                return True
            else:
                logger.error(f"Docker build failed with exit code {exit_code}")
                return False
                
        except Exception as e:
            logger.error(f"Docker run error: {e}", exc_info=True)
            return False
    
    def _run_build_with_mutagen(self, working_dir: str = ".") -> bool:
        """Run build with Mutagen synchronization for remote Docker"""
        logger = get_logger(__name__)
        container_name = f"{self.docker_config['container_prefix']}-build"
        image_tag = f"{self.docker_config['image_name']}:{self.docker_config['build_tag']}"
        working_path = Path(working_dir).resolve()
        container = None

        try:
            # Start container for Mutagen
            container = self._start_container_for_mutagen(container_name, image_tag)
            if not container:
                return False
            
            # Create and manage Mutagen sync (without outputs/ in ignore)
            sync_manager = MutagenSessionManager(container_name, working_path)
            
            logger.debug("Creating Mutagen session for build...")
            session_created = sync_manager.create_session()
            
            if not session_created:
                logger.error("Failed to establish Mutagen sync")
                container.stop()
                container.remove()
                return False
            
            # Ensure outputs directory exists in container
            logger.info("Preparing build environment...")
            exec_result = container.exec_run("mkdir -p /app/outputs")
            if exec_result.exit_code != 0:
                logger.warning("Failed to create outputs directory")
            
            # Now run the actual build
            logger.info("Starting build process...")
            exec_result = container.exec_run(
                ["python", "build.py"],
                stream=False,  # Don't stream, get exit code
                demux=False
            )
            
            # Check exit code first
            build_success = exec_result.exit_code == 0
            
            # Log the output
            if exec_result.output:
                output_lines = exec_result.output.decode('utf-8').splitlines()
                for line in output_lines:
                    if line.strip():
                        logger.info(line)
            
            if build_success:
                # Create tar.gz archive in container
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                zip_name = f"phantom-docs-build-docker-remote-{timestamp}.tar.gz"
                
                logger.info("Creating build archive...")
                
                # Use tar with gzip
                zip_result = container.exec_run(
                    ["sh", "-c", f"cd /app && tar -czf /tmp/{zip_name} outputs/"]
                )
                
                if zip_result.exit_code == 0:
                    # Copy ZIP to local outputs directory
                    logger.info("Copying build archive from container...")
                    
                    # Ensure local outputs directory exists
                    local_outputs = Path("outputs")
                    local_outputs.mkdir(exist_ok=True)
                    
                    # Use Docker SDK to get the archive
                    try:
                        # Get the archive as a tar stream
                        bits, stat = container.get_archive(f'/tmp/{zip_name}')
                        
                        # Write the archive locally
                        import tarfile
                        import io
                        
                        # Create a BytesIO object from the bits generator
                        tar_data = io.BytesIO()
                        for chunk in bits:
                            tar_data.write(chunk)
                        tar_data.seek(0)
                        
                        # Extract the ZIP file from the tar archive
                        with tarfile.open(fileobj=tar_data, mode='r') as tar:
                            # Find and extract the ZIP file
                            for member in tar.getmembers():
                                if member.name == zip_name:
                                    # Extract directly to outputs directory
                                    tar.extract(member, path=str(local_outputs))
                                    logger.info(f"✓ Build archive saved: outputs/{zip_name}")
                                    build_success = True
                                    break
                            else:
                                logger.error("ZIP file not found in tar archive")
                                build_success = False
                                
                    except APIError as e:
                        logger.error(f"Failed to copy build archive: {e}")
                        build_success = False
                else:
                    logger.error(f"Failed to create build archive: {zip_result.output.decode() if zip_result.output else 'No output'}")
                    # Check if outputs directory exists and has content
                    check_outputs = container.exec_run(["ls", "-la", "/app/outputs/"])
                    logger.error(f"outputs directory content: {check_outputs.output.decode() if check_outputs.output else 'No output'}")
                    build_success = False
            
            # Terminate mutagen session
            sync_manager.terminate_session()

            if build_success:
                logger.info("Remote Docker build completed successfully")
                return True
            else:
                logger.error("Remote Docker build failed")
                return False
                
        except Exception as e:
            logger.error(f"Docker build error: {e}", exc_info=True)
            # Cleanup on error - keep it simple like serve
            if container:
                try:
                    container.stop()
                    container.remove()
                except (docker.errors.APIError, docker.errors.NotFound):
                    pass
            return False
    
            
    def run_serve(self, working_dir: str = ".", port: int = 8000) -> None:
        """Run serve in Docker container with hot reload"""
        logger = get_logger(__name__)
        
        # Detect environment and choose strategy
        env = self.detect_docker_environment()
        
        if env['sync_strategy'] == 'volumes':
            # Existing local Docker implementation
            self._run_serve_with_volumes(working_dir, port)
        elif env['sync_strategy'] == 'mutagen':
            logger.info("Remote Docker detected - using Mutagen synchronization")
            logger.info(f"Mutagen version: {env['mutagen_version']}")
            self._run_serve_with_mutagen(working_dir, port)
        else:
            logger.error("Remote Docker detected but Mutagen not installed")
            logger.error("Please install Mutagen to enable file synchronization")
            logger.error("  macOS: brew install mutagen-io/mutagen/mutagen")
            logger.error("  Linux: Download from https://github.com/mutagen-io/mutagen/releases")
    
    def _run_serve_with_volumes(self, working_dir: str = ".", port: int = 8000) -> None:
        """Original run_serve implementation with volume mappings"""
        logger = get_logger(__name__)
        if not self.client:
            return
            
        container_name = f"{self.docker_config['container_prefix']}-serve"
        image_tag = f"{self.docker_config['image_name']}:{self.docker_config['build_tag']}"
        
        # Prepare volumes for hot reload
        working_path = Path(working_dir).resolve()
        volumes = self._prepare_volumes(working_path)
        
        # Port mapping
        ports = {f"{port}/tcp": port}
        
        try:
            # Remove existing container if any
            self._remove_existing_container(container_name)
                
            logger.info("Starting Docker container...")
            
            # Run container
            container = self.client.containers.run(
                image=image_tag,
                name=container_name,
                volumes=volumes,
                ports=ports,
                command=["python", "serve.py"],
                detach=True,
                remove=False,
                working_dir="/app",
                environment={
                    "PYTHONUNBUFFERED": "1",  # For real-time log output
                    "DOCKER_MODE": "1"  # Flag to indicate Docker mode
                }
            )
            self.container = container
            # Stream logs until interrupted
            for log in container.logs(stream=True, follow=True):
                # Decode and process log line
                log_line = log.decode('utf-8').rstrip()
                if log_line:
                    # Route container logs through our logger
                    logger.info(log_line)
                
        except Exception as e:
            logger.error(f"Docker serve error: {e}", exc_info=True)
            if self.container:
                self.container.stop()
                self.container.remove()
    
    def _run_serve_with_mutagen(self, working_dir: str = ".", port: int = 8000) -> None:
        """Run container with Mutagen synchronization for remote Docker"""
        logger = get_logger(__name__)
        container_name = f"{self.docker_config['container_prefix']}-serve"
        image_tag = f"{self.docker_config['image_name']}:{self.docker_config['build_tag']}"
        working_path = Path(working_dir).resolve()
        
        try:
            # Start container for Mutagen
            container = self._start_container_for_mutagen(container_name, image_tag)
            if not container:
                return
            
            # Create and manage Mutagen sync with port mappings
            sync_manager = MutagenSessionManager(
                container_name, 
                working_path,
                port_mappings={port: port}  # Container port 8000 -> Local port (user specified)
            )
            
            logger.debug("Creating Mutagen session...")
            session_created = sync_manager.create_session()
            logger.debug(f"Session creation result: {session_created}")
            
            if not session_created:
                logger.error("Failed to establish Mutagen sync")
                container.stop()
                container.remove()
                return
            
            # Create port forward for remote Docker
            logger.debug("Creating port forward...")
            if not sync_manager.create_port_forward():
                logger.error("Failed to create port forward")
                sync_manager.terminate_session()
                container.stop()
                container.remove()
                return
            
            logger.debug("Starting sync monitor...")
            # Start monitor
            sync_manager.start_monitor(logger_integration=True)
            
            logger.debug("Monitor started, preparing to start development server...")
            # Now that files are synced, start the actual serve process
            logger.info("Starting development server...")
            exec_result = container.exec_run(
                ["python", "serve.py"],
                stream=True,
                demux=True,
                environment={
                    "PYTHONUNBUFFERED": "1",
                    "DOCKER_MODE": "1",
                    "DOCKER_REMOTE_SERVE": "1"
                }
            )
            
            logger.info("File changes will be synchronized automatically")
            logger.info("Press Ctrl+C to stop")
            
            self.container = container
            
            # Stream exec output until interrupted
            try:
                if exec_result.output:
                    for stdout_data, stderr_data in exec_result.output:
                        if stdout_data:
                            for line in stdout_data.decode('utf-8').splitlines():
                                if line.strip():
                                    logger.info(line)
                        if stderr_data:
                            for line in stderr_data.decode('utf-8').splitlines():
                                if line.strip():
                                    logger.error(line)
            except KeyboardInterrupt:
                sync_manager.terminate_session()

        except Exception as e:
            logger.error(f"Docker serve error: {e}", exc_info=True)
            if self.container:
                self.container.stop()
                self.container.remove()
    
    # noinspection PyMethodMayBeStatic
    def _wait_for_container_ready(self, container, max_retries: int = 30) -> bool:
        """Wait for container to be in running state"""
        logger = get_logger(__name__)
        
        for i in range(max_retries):
            try:
                # Reload container state
                container.reload()
                
                # Check if container is running
                if container.status == 'running':
                    # Additional check: try to exec a simple command
                    try:
                        result = container.exec_run("echo 'ready'", demux=True)
                        if result.exit_code == 0:
                            logger.info("Container is ready")
                            return True
                    except Exception as e:
                        logger.debug(f"Container exec check failed: {e}")
                
                # Container is not running yet
                if container.status in ['exited', 'dead']:
                    logger.error(f"Container is in {container.status} state")
                    # Get logs for debugging
                    logs = container.logs(tail=50).decode('utf-8')
                    if logs:
                        logger.error(f"Container logs:\n{logs}")
                    return False
                
                # Still starting up
                if i < max_retries - 1:
                    time.sleep(1)
                    
            except Exception as e:
                logger.debug(f"Error checking container status: {e}")
                if i < max_retries - 1:
                    time.sleep(1)
                else:
                    return False
        
        logger.error("Container failed to become ready within timeout")
        return False
    
    def _remove_existing_container(self, container_name: str, force: bool = False) -> None:
        """Remove existing container if it exists
        
        Args:
            container_name: Name of the container to remove
            force: If True, forcefully remove the container. If False, stop then remove.
        """
        logger = get_logger(__name__)
        try:
            old_container = self.client.containers.get(container_name)
            if force:
                logger.warning("Removing existing container...")
                old_container.remove(force=True)
            else:
                logger.warning("Stopping existing container...")
                old_container.stop()
                old_container.remove()
        except (docker.errors.NotFound, NotFound):
            pass
    
    def _start_container_for_mutagen(self, container_name: str, image_tag: str) -> Optional[Any]:
        """Start a container for Mutagen synchronization
        
        Args:
            container_name: Name for the container
            image_tag: Docker image tag to use
            
        Returns:
            Container object if successful, None otherwise
        """
        logger = get_logger(__name__)
        
        # Remove existing container if any
        self._remove_existing_container(container_name)
        
        logger.info("Starting Docker container...")
        
        # Start container WITHOUT volume/port mappings for remote Docker
        # Use a keep-alive command since we need to set up Mutagen first
        container = self.client.containers.run(
            image=image_tag,
            name=container_name,
            command=["tail", "-f", "/dev/null"],  # Keep container running
            detach=True,
            remove=False,
            working_dir="/app",
            environment={
                "PYTHONUNBUFFERED": "1",
                "DOCKER_MODE": "1"
            }
            # Note: No volumes or ports parameter!
        )
        
        # Wait for container to be fully running
        logger.info("Waiting for container to be ready...")
        if not self._wait_for_container_ready(container):
            logger.error("Container failed to start properly")
            container.stop()
            container.remove()
            return None
            
        return container
                
    def cleanup(self):
        """Clean up resources"""
        logger = get_logger(__name__)
        if self.container:
            try:
                logger.info("Cleaning up container...")
                self.container.stop(timeout=5)
                self.container.remove()
                logger.info("Cleanup completed")
            except Exception as e:
                logger.warning(f"Cleanup warning: {e}")
                # Try force removal
                try:
                    self.container.remove(force=True)
                except (docker.errors.APIError, docker.errors.NotFound):
                    pass
        if self.client:
            self.client.close()


class MutagenSessionManager:
    """Manages Mutagen synchronization sessions"""
    
    def __init__(self, container_name: str, local_path: Path, port_mappings: Dict[int, int] = None):
        self.container_name = container_name
        self.local_path = local_path
        self.session_name = f"phantom-{container_name}-{int(time.time())}"
        self.forward_session_prefix = f"phantom-forward-{container_name}"
        self.monitor_thread = None
        self.port_mappings = port_mappings or {}  # {container_port: local_port}
        self.active_forward_sessions = []  # Track created forward sessions
    
    @staticmethod
    def _create_subprocess(cmd: list) -> subprocess.Popen:
        """Create subprocess with UTF-8 encoding
        
        Args:
            cmd: Command to execute
            
        Returns:
            Popen object
        """
        # Use explicit UTF-8 encoding for all platforms
        return subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1
        )

    def create_session(self) -> bool:
        """Create Mutagen sync session"""
        logger = get_logger(__name__)

        # Clean up existing sessions
        subprocess.run(['mutagen', 'sync', 'terminate', '--all'], capture_output=True)

        # Build command with ignore patterns matching _prepare_volumes
        cmd = [
            'mutagen', 'sync', 'create',
            '--name', self.session_name,
            str(self.local_path),
            f'docker://{self.container_name}/app',
            '--sync-mode', 'two-way-resolved',
            '--watch-mode', 'force-poll',
            '--watch-polling-interval', '2',
            # Ignore patterns matching _prepare_volumes exclude_items
            '--ignore', 'node_modules/',
            '--ignore', 'package-lock.json',
            '--ignore', '.npm/',
            '--ignore', '.cache/',
            '--ignore', '.DS_Store',
            # Additional patterns for development environments
            '--ignore', '.venv/',
            '--ignore', 'venv/',
            '--ignore', '__pycache__/',
            '--ignore', '*.pyc',
            '--ignore', '.git/',
            '--ignore', '.idea/',
            '--ignore', '.vscode/',
            '--ignore', 'logs/',
            # Always ignore outputs directory
            '--ignore', 'outputs/',
            '--ignore', 'outputs/**'
        ]

        # Log the full command for debugging
        logger.info(f"Running Mutagen create command: {' '.join(cmd)}")

        # Run command with real-time output
        process = self._create_subprocess(cmd)

        # Capture output
        stdout_lines = []
        stderr_lines = []

        # Simple blocking read for all platforms
        for line in iter(process.stdout.readline, ''):
            if line:
                line = line.rstrip()
                stdout_lines.append(line)
                logger.info(f"[Mutagen] {line}")
        
        # Wait for process to complete
        return_code = process.wait()
        
        # Get any remaining stderr
        stderr_output = process.stderr.read()
        if stderr_output:
            for line in stderr_output.splitlines():
                if line.strip():
                    stderr_lines.append(line)
                    logger.warning(f"[Mutagen] {line}")

        if return_code == 0:
            logger.info(f"Created Mutagen session: {self.session_name}")
            sync_result = self._wait_for_initial_sync()
            logger.debug(f"_wait_for_initial_sync returned: {sync_result}")
            return sync_result
        else:
            logger.error(f"Failed to create Mutagen session (exit code: {return_code})")
            if stderr_lines:
                logger.error(f"Error output:\n" + '\n'.join(stderr_lines))
            return False

    def _wait_for_initial_sync(self, timeout: int = 300) -> bool:
        """Wait for initial sync to complete"""
        logger = get_logger(__name__)
        last_status = None
        start_time = time.time()

        logger.info("Waiting for initial file synchronization...")

        while True:
            # Check timeout
            if time.time() - start_time > timeout:
                logger.error(f"Initial sync did not complete within {timeout} seconds")
                return False

            # Run sync list command with UTF-8 encoding
            result = subprocess.run(
                ['mutagen', 'sync', 'list', self.session_name, '-l'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )

            if result.returncode == 0:
                output = result.stdout

                # Extract current status
                status_match = re.search(r'Status:\s*(\w+)', output)
                if status_match:
                    current_status = status_match.group(1).lower()

                    # Log status changes
                    if current_status != last_status:
                        if current_status == 'watching':
                            logger.info("Initial synchronization completed successfully")
                        elif current_status == 'staging':
                            # Extract file count if available
                            files_match = re.search(r'(\d+)\s+entr(?:y|ies)', output)
                            if files_match:
                                file_count = files_match.group(1)
                                logger.info(f"Staging {file_count} files for synchronization...")
                            else:
                                logger.info("Staging files for synchronization...")
                        elif current_status == 'transitioning':
                            logger.info("Transitioning sync state...")
                        elif current_status == 'reconciling':
                            logger.info("Reconciling file differences...")
                        elif current_status == 'scanning':
                            logger.info("Scanning files for changes...")
                        last_status = current_status

                    # Check if sync is complete and watching
                    if current_status == 'watching':
                        logger.debug("Status is 'watching', checking for conflicts/problems...")

                        # Check for conflicts or problems in the output
                        has_conflicts = False
                        has_problems = False

                        # Look for conflict/problem indicators
                        for line in output.split('\n'):
                            line_lower = line.lower()
                            if 'conflicts:' in line_lower:
                                if 'none' not in line_lower:
                                    has_conflicts = True
                                    logger.debug(f"Found conflicts line: {line}")
                            elif 'problems:' in line_lower:
                                if 'none' not in line_lower:
                                    has_problems = True
                                    logger.debug(f"Found problems line: {line}")

                        if has_conflicts:
                            logger.warning("Sync conflicts detected, waiting for resolution...")
                        elif has_problems:
                            logger.warning("Sync problems detected, waiting for resolution...")
                        else:
                            logger.debug("No conflicts or problems detected, verifying stability...")
                            # No conflicts or problems, verify stability
                            time.sleep(1)

                            # Quick verification
                            verify_result = subprocess.run(
                                ['mutagen', 'sync', 'list', self.session_name],
                                capture_output=True,
                                text=True,
                                encoding='utf-8',
                                errors='replace'
                            )

                            if verify_result.returncode == 0:
                                # Check status in output (case-insensitive)
                                verify_output = verify_result.stdout.lower()
                                if 'status: watching' in verify_output or 'watching for changes' in verify_output:
                                    logger.info("File synchronization verified and stable")
                                    return True
                                else:
                                    logger.debug(f"Verification status not watching yet: {verify_result.stdout}")
                            else:
                                logger.debug(f"Verification failed: {verify_result.stderr}")

                # Check for errors (but not in the status line itself)
                error_lines = [line for line in output.split('\n') if 'error' in line.lower() and 'status:' not in line.lower()]
                if error_lines:
                    logger.error(f"Sync error detected: {output}")
                    return False
            else:
                logger.debug(f"Failed to get sync status: {result.stderr}")

            # Short sleep before next check
            time.sleep(0.5)

    def start_monitor(self, logger_integration: bool = True):
        """Start Mutagen monitor with logger integration"""

        # Use logger_integration parameter even if it's always True for now
        if not logger_integration:
            # Future: Could implement non-logger version
            pass

        def monitor_output():
            cmd = ['mutagen', 'sync', 'monitor', '-l', self.session_name]
            process = self._create_subprocess(cmd)
            logger = get_logger('mutagen.sync')
            try:
                for line in iter(process.stdout.readline, ''):
                    if line:
                        line = line.strip()
                        if 'Watching' in line:
                            logger.info(f"Status: {line}")
                        elif 'Scanning' in line:
                            logger.info(f"Scanning: {line}")
                        elif 'Applying' in line:
                            logger.info(f"Applying changes: {line}")
                        elif 'error' in line.lower():
                            logger.error(f"Sync error: {line}")
                        elif line:
                            logger.debug(line)
            except UnicodeDecodeError as e:
                logger.debug(f"Unicode decode error in monitor: {e}")
            except Exception as e:
                logger.debug(f"Monitor error: {e}")
            finally:
                process.wait()

        self.monitor_thread = threading.Thread(target=monitor_output, daemon=True)
        self.monitor_thread.start()
    
    def create_port_forward(self) -> bool:
        """Create Mutagen forward session for port forwarding"""
        logger = get_logger(__name__)
        
        if not self.port_mappings:
            logger.debug("No port mappings configured, skipping port forward")
            return True
        
        logger.info("Setting up port forwarding...")
        
        for container_port, local_port in self.port_mappings.items():
            forward_name = f"{self.forward_session_prefix}-{local_port}"
            
            # Terminate any existing forward with same name
            subprocess.run(
                ['mutagen', 'forward', 'terminate', forward_name],
                capture_output=True
            )
            
            cmd = [
                'mutagen', 'forward', 'create',
                '--name', forward_name,
                f"tcp:localhost:{local_port}",
                f"docker://{self.container_name}:tcp:localhost:{container_port}"
            ]
            
            logger.info(f"Creating port forward: localhost:{local_port} -> container:{container_port}")
            logger.debug(f"Command: {' '.join(cmd)}")
            
            # Run command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            if result.returncode == 0:
                logger.info(f"✓ Port forward created: {forward_name}")
                self.active_forward_sessions.append(forward_name)
            else:
                logger.error(f"Failed to create port forward: {result.stderr}")
                # Clean up any previously created forwards
                self.terminate_port_forward()
                return False
        
        # Verify forwards are working
        time.sleep(1)  # Give forwards time to establish
        return self._verify_port_forwards()
    
    def _verify_port_forwards(self) -> bool:
        """Verify that port forwards are active"""
        logger = get_logger(__name__)
        
        for forward_name in self.active_forward_sessions:
            result = subprocess.run(
                ['mutagen', 'forward', 'list', forward_name],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            if result.returncode != 0:
                logger.error(f"Port forward {forward_name} is not active")
                return False
            
            # Check for connected state in output
            if 'connected' in result.stdout.lower():
                logger.debug(f"Port forward {forward_name} is connected")
            else:
                logger.warning(f"Port forward {forward_name} may not be fully connected")
        
        return True
    
    def terminate_port_forward(self):
        """Terminate all port forwarding sessions"""
        logger = get_logger(__name__)
        
        for forward_name in self.active_forward_sessions:
            logger.debug(f"Terminating port forward: {forward_name}")
            subprocess.run(
                ['mutagen', 'forward', 'terminate', forward_name],
                capture_output=True
            )
        
        if self.active_forward_sessions:
            logger.info(f"Terminated {len(self.active_forward_sessions)} port forward sessions")
            self.active_forward_sessions.clear()
    
    def terminate_session(self):
        """Terminate Mutagen sync and forward sessions"""
        logger = get_logger(__name__)
        
        # Terminate sync session
        subprocess.run(
            ['mutagen', 'sync', 'terminate', self.session_name],
            capture_output=True
        )
        logger.info(f"Terminated Mutagen sync session: {self.session_name}")
        
        # Terminate port forwards
        self.terminate_port_forward()