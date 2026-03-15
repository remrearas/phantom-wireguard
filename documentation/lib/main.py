"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Phantom Documentation Kit - Main Library
Common functions and classes for build and serve scripts
"""

import sys
import os
import subprocess
import shutil
import json
import platform
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
from textwrap import dedent

# 1. Configuration Management
def load_config(config_file: str = 'config.json') -> Dict:
    """Load and validate configuration"""
    config_path = Path(config_file)
    if not config_path.exists():
        # Can't use logger here as it depends on config being loaded
        # So we keep print for bootstrap errors
        print(f"Configuration file '{config_file}' not found!")
        print("Please ensure config.json exists in the project root.")
        sys.exit(1)
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# 2. Colors Class
class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# 3. Command Execution
def run_command(cmd: List[str], cwd: Optional[str] = None, 
                capture_output: bool = True, stream_to_logger: bool = False) -> Optional[subprocess.CompletedProcess]:
    """Run a command with cross-platform compatibility
    
    Args:
        cmd: Command and arguments to run
        cwd: Working directory
        capture_output: If True, capture stdout/stderr. If False, inherit parent's streams
        stream_to_logger: If True and capture_output is False, stream output through logger
    """
    # Import logger here to avoid circular dependency
    from .logging import get_logger
    logger = get_logger(__name__)
    
    try:
        
        # For streaming output through logger
        if stream_to_logger and not capture_output:
            import threading
            
            def stream_output(pipe, logger_func):
                """Stream output from pipe to logger"""
                for line in iter(pipe.readline, ''):
                    if line:
                        line = line.rstrip()
                        # Parse mkdocs output format
                        if line.startswith('INFO'):
                            logger_func(line[4:].strip().lstrip('-').strip())
                        elif line.startswith('WARNING'):
                            logger.warning(line[7:].strip().lstrip('-').strip())
                        elif line.startswith('ERROR'):
                            logger.error(line[5:].strip().lstrip('-').strip())
                        else:
                            # For lines without log level prefix
                            logger_func(line)
                pipe.close()
            
            # Start process with pipes
            # Windows fix: Use shell=True for npm/node commands
            shell = platform.system().lower() == 'windows' and cmd[0] in ['npm', 'node']
            process = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding='utf-8',  # Use explicit UTF-8 encoding
                errors='replace',  # Replace decode errors with ?
                bufsize=1,  # Line buffered
                shell=shell
            )
            
            # Create threads to read output
            stdout_thread = threading.Thread(
                target=stream_output,
                args=(process.stdout, logger.info)
            )
            stderr_thread = threading.Thread(
                target=stream_output,
                args=(process.stderr, logger.error)
            )
            
            stdout_thread.start()
            stderr_thread.start()
            
            # Wait for process to complete
            process.wait()
            stdout_thread.join()
            stderr_thread.join()
            
            return subprocess.CompletedProcess(cmd, process.returncode)
        
        # Original behavior for non-streaming mode
        # Windows fix: Use shell=True for npm/node commands
        shell = platform.system().lower() == 'windows' and cmd[0] in ['npm', 'node']
        result = subprocess.run(
            cmd, 
            cwd=cwd, 
            capture_output=capture_output, 
            encoding='utf-8',  # Use explicit UTF-8 encoding
            errors='replace',  # Replace decode errors with ?
            shell=shell
        )
        return result
    except subprocess.SubprocessError as ex:
        logger.error(f"Error running command {' '.join(cmd)}: {ex}")
        return None
    except OSError as ex:
        logger.error(f"OS error running command {' '.join(cmd)}: {ex}")
        return None

# 4. Dependency Checks
def check_mkdocs() -> bool:
    """Check if MkDocs is installed as a Python package"""
    try:
        import mkdocs
        return True
    except ImportError:
        from .logging import get_logger
        logger = get_logger(__name__)
        logger.error("MkDocs is not installed")
        logger.error("Please install requirements: pip install -r requirements.txt")
        return False


# noinspection PyDeprecation
def check_node() -> bool:
    """Check if Node.js is installed"""
    return shutil.which('node') is not None


def check_docker_package() -> bool:
    """Check if Docker Python package is installed"""
    try:
        import docker
        return True
    except ImportError:
        return False

def check_docker_environment() -> Dict[str, Any]:
    """Check Docker environment (local or remote)
    
    Returns:
        Dict with keys:
        - 'type': 'local' or 'remote'
        - 'available': True if Docker is available
        - 'docker_host': DOCKER_HOST value if remote
        - 'error': Error message if not available
    """
    from .logging import get_logger
    logger = get_logger(__name__)
    
    docker_host = os.environ.get('DOCKER_HOST')
    is_remote = bool(docker_host)
    
    result = {
        'type': 'remote' if is_remote else 'local',
        'docker_host': docker_host,
        'available': False,
        'error': None
    }
    
    # Check if Docker Python package is installed
    if not check_docker_package():
        result['error'] = "Docker Python package is not installed. Install it with: pip install docker"
        return result
    
    # Try to connect to Docker
    try:
        import docker
        client = docker.from_env()
        client.ping()
        result['available'] = True
        logger.debug(f"Connected to {'remote' if is_remote else 'local'} Docker daemon")
    except Exception as e:
        if is_remote:
            result['error'] = f"Cannot connect to Docker daemon at {docker_host}: {str(e)}"
        else:
            result['error'] = "Docker daemon is not running. Please start Docker."
    
    return result


# noinspection PyDeprecation
def check_mutagen() -> bool:
    """Check if Mutagen is installed"""
    return shutil.which('mutagen') is not None

# 5. Vendor Management
class VendorManager:
    """Handles vendor dependency checking and building"""
    def __init__(self, config: Dict):
        self.config = config
        self.vendor_dir = Path(config['paths']['vendor_dir'])
        self.vendor_builder_dir = Path(config['paths']['vendor_builder_dir'])
        self.dependencies_file = self.vendor_builder_dir / "dependencies.json"
        
    def check_dependencies(self) -> bool:
        """Check if vendor files exist"""
        if not self.vendor_dir.exists():
            return False
            
        if not self.dependencies_file.exists():
            return False
            
        try:
            with open(self.dependencies_file, 'r', encoding='utf-8') as deps_file:
                deps = json.load(deps_file)
                
            for dep in deps.get('dependencies', []):
                expected_filename = VendorManager.get_expected_filename(dep)
                file_path = self.vendor_dir / expected_filename
                if not file_path.exists():
                    return False
                    
            # Check for webfonts directory
            if not (self.vendor_dir / 'webfonts').exists():
                return False
                
            return True
            
        except (json.JSONDecodeError, IOError, OSError):
            return False
        
    def build_dependencies(self) -> bool:
        """Build vendor files"""
        if not self.vendor_builder_dir.exists():
            from .logging import get_logger
            logger = get_logger(__name__)
            logger.error("Vendor builder directory not found")
            return False
            
        if not check_node():
            from .logging import get_logger
            logger = get_logger(__name__)
            logger.error("Node.js is required for vendor build")
            return False
            
        original_dir = os.getcwd()
        try:
            os.chdir(self.vendor_builder_dir)
            
            # Install dependencies if needed
            if not Path("node_modules").exists():
                result = run_command(['npm', 'install'])
                if result and result.returncode != 0:
                    os.chdir(original_dir)
                    return False
                    
            # Build vendor files
            result = run_command(['npm', 'run', 'build'])
            os.chdir(original_dir)
            
            return result and result.returncode == 0
            
        except (subprocess.SubprocessError, OSError, IOError):
            os.chdir(original_dir)
            return False

    @staticmethod
    def get_expected_filename(dep: Dict) -> str:
        """Get expected filename with minification logic"""
        expected_filename = dep['to']
        if dep.get('minify', False) and '.min.' not in dep['from']:
            if dep['type'] == 'js' and not expected_filename.endswith('.min.js'):
                expected_filename = expected_filename.replace('.js', '.min.js')
            elif dep['type'] == 'css' and not expected_filename.endswith('.min.css'):
                expected_filename = expected_filename.replace('.css', '.min.css')
        return expected_filename

# 6. MkDocs Integration
def setup_mkdocs_logging():
    """Set up MkDocs logging to integrate with our logger"""
    from .logging import get_logger
    logger_ = get_logger(__name__)
    
    # Set up MkDocs logging to use our logger
    mkdocs_logger = logging.getLogger('mkdocs')
    mkdocs_logger.setLevel(logging.INFO)
    mkdocs_logger.propagate = False  # Prevent duplicate logs
    
    # Create a custom handler that forwards to our logger
    class MkDocsLogHandler(logging.Handler):
        def emit(self, record):
            msg = self.format(record)
            if record.levelno >= logging.ERROR:
                logger_.error(msg)
            elif record.levelno >= logging.WARNING:
                logger_.warning(msg)
            else:
                logger_.info(msg)
    
    # Clear existing handlers and add our custom handler
    mkdocs_logger.handlers.clear()
    handler = MkDocsLogHandler()
    handler.setFormatter(logging.Formatter('%(message)s'))
    mkdocs_logger.addHandler(handler)
    
    # Also capture sub-loggers
    for logger_name in ['mkdocs.commands', 'mkdocs.structure', 'mkdocs.plugins']:
        sub_logger = logging.getLogger(logger_name)
        sub_logger.handlers.clear()
        sub_logger.addHandler(handler)
        sub_logger.setLevel(logging.INFO)
        sub_logger.propagate = False  # Prevent duplicate logs

# 7. Banner Display
def print_banner(mode: str = "build"):
    """Display banner with ASCII art"""
    # Skip banner in Docker container mode
    if os.environ.get('DOCKER_MODE') == '1':
        return
        
    banner = dedent("""
        ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
        ██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
        ██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
        ██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
        ██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
        ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
        Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
    """).strip()
    
    print(banner)

    if mode == "build":
        print("Building Phantom Documentation Kit...")
    else:
        print("Starting Phantom Documentation Kit Server...")
    print()