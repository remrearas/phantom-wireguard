"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Pytest configuration and fixtures for Secure Deployment User tests

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
"""

import sys
import tempfile
import shutil
import zipfile
import importlib.util
import logging
from pathlib import Path
from typing import Generator, Dict
from textwrap import dedent

import pytest
import gnupg

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# DYNAMIC MODULE IMPORT
# ============================================================================

def import_deployment_watcher():
    """
    Dynamically import deployment-watcher.py using importlib
    This is needed because the filename contains a hyphen
    """
    watcher_path = Path(__file__).parent.parent / 'scripts' / 'deployment-watcher.py'

    # Create temp log directory for import
    temp_log_dir = Path(tempfile.mkdtemp(prefix='deployment-log-'))
    temp_log_file = temp_log_dir / 'deployment.log'

    # Read the module code and patch LOG_FILE before execution
    with open(watcher_path, 'r') as f:
        code = f.read()

    # Replace LOG_FILE path with temp path
    code = code.replace(
        'LOG_FILE = Path("/var/log/deployment.log")',
        f'LOG_FILE = Path("{temp_log_file}")'
    )

    # Compile and execute the patched code
    spec = importlib.util.spec_from_file_location('deployment_watcher', watcher_path)
    if spec is None:
        raise ImportError(f"Cannot load deployment-watcher.py from {watcher_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules['deployment_watcher'] = module

    # Execute the patched code instead of the original
    exec(compile(code, str(watcher_path), 'exec'), module.__dict__)

    # Cleanup temp log dir
    shutil.rmtree(temp_log_dir, ignore_errors=True)

    return module


# Import deployment-watcher module
deployment_watcher = import_deployment_watcher()


@pytest.fixture
def temp_dirs() -> Generator[Dict[str, Path], None, None]:
    """Create temporary directories for testing"""
    base_dir = Path(tempfile.mkdtemp(prefix='deployment-test-'))

    dirs = {
        'base': base_dir,
        'quarantine': base_dir / 'incoming',
        'outputs': base_dir / 'outputs',
        'deployment': base_dir / 'deployment',
        'secrets': base_dir / 'secrets',
        'locks': base_dir / 'locks',
        'logs': base_dir / 'logs',
        'gpg_home': base_dir / 'gpg',
    }

    # Create all directories
    for dir_path in dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)

    # GPG home needs special permissions
    dirs['gpg_home'].chmod(0o700)

    yield dirs

    # Cleanup
    shutil.rmtree(base_dir, ignore_errors=True)


@pytest.fixture(scope="session")
def shared_gpg_key() -> Generator[Dict[str, any], None, None]:
    """
    Session-wide shared GPG key pair for Docker integration tests

    This key is used across all Docker integration tests to maintain consistency:
    - Public key is imported to container once
    - Private key remains available for signing test packages
    - Cleaned up at end of test session
    """
    # Create isolated GPG home for session
    gpg_home = Path(tempfile.mkdtemp(prefix='gpg-session-'))
    gpg_home.chmod(0o700)

    # Initialize GPG
    gpg = gnupg.GPG(gnupghome=str(gpg_home))

    # Generate key pair
    input_data = gpg.gen_key_input(
        **{
            'key_type': 'RSA',
            'key_length': 2048,
            'name_real': 'Test Deployment Key',
            'name_email': 'test@deployment.local',
            'passphrase': '',
            'no_protection': True
        }
    )

    key = gpg.gen_key(input_data)

    if not key:
        pytest.skip(f"GPG key generation failed: {key.stderr if hasattr(key, 'stderr') else 'Unknown error'}")

    # Export public key
    pubkey = gpg.export_keys(str(key))

    if not pubkey:
        pytest.skip("GPG key export failed")

    logger.info(f"Created session GPG key: {key}")

    yield {
        'key_id': str(key),
        'email': 'test@deployment.local',
        'gpg_home': gpg_home,
        'gpg': gpg,
        'pubkey': pubkey,
    }

    # Session cleanup
    shutil.rmtree(gpg_home, ignore_errors=True)
    logger.info("Cleaned up session GPG key")


@pytest.fixture
def gpg_key(temp_dirs: Dict[str, Path]) -> Generator[Dict[str, any], None, None]:
    """Create an isolated test GPG key pair using python-gnupg (stable, no segfault)"""
    gpg_home = temp_dirs['gpg_home']

    # Initialize GPG with isolated home directory
    gpg = gnupg.GPG(gnupghome=str(gpg_home))

    # Generate key using python-gnupg (much more stable than subprocess)
    input_data = gpg.gen_key_input(
        **{
            'key_type': 'RSA',
            'key_length': 2048,
            'name_real': 'Test Deployment Key',
            'name_email': 'test@deployment.local',
            'passphrase': '',
            'no_protection': True
        }
    )

    key = gpg.gen_key(input_data)

    if not key:
        pytest.skip(f"GPG key generation failed: {key.stderr if hasattr(key, 'stderr') else 'Unknown error'}")

    # Export public key
    pubkey_content = gpg.export_keys(str(key))

    if not pubkey_content:
        pytest.skip("GPG key export failed")

    # Save public key for reference
    pubkey_file = temp_dirs['secrets'] / 'deployment.asc'
    pubkey_file.write_text(pubkey_content)

    yield {
        'email': 'test@deployment.local',
        'home': gpg_home,
        'pubkey': pubkey_file,
        'key_id': str(key),
    }

    # Cleanup is handled by temp_dirs fixture


@pytest.fixture
def valid_deployment_script() -> str:
    """Return a valid run.sh content"""
    return dedent("""
        #!/bin/bash
        # Test deployment script
        echo "Deployment script started"
        exit 0
    """).strip()


@pytest.fixture
def deployment_package(
        temp_dirs: Dict[str, Path],
        gpg_key: Dict[str, any],
        valid_deployment_script: str
) -> Dict[str, Path]:
    """Create a valid test deployment package"""
    pkg_dir = temp_dirs['base'] / 'package'
    pkg_dir.mkdir()

    files_dir = pkg_dir / 'files'
    files_dir.mkdir()

    # Create run.sh
    deployment_script = pkg_dir / 'run.sh'
    deployment_script.write_text(valid_deployment_script)

    # Create test files
    (files_dir / 'test1.txt').write_text('Test file 1\n')
    (files_dir / 'test2.txt').write_text('Test file 2\n')
    (files_dir / 'config.json').write_text('{"test": true}\n')

    # Create subdirectory with files
    subdir = files_dir / 'subdir'
    subdir.mkdir()
    (subdir / 'nested.txt').write_text('Nested file content\n')

    # Create deployment.zip
    deployment_zip = temp_dirs['base'] / 'deployment.zip'
    with zipfile.ZipFile(deployment_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(deployment_script, 'run.sh')
        for file in files_dir.rglob('*'):
            if file.is_file():
                arcname = f"files/{file.relative_to(files_dir)}"
                zf.write(file, arcname)

    # Sign deployment.zip using python-gnupg (stable, no segfault)
    deployment_sig = temp_dirs['base'] / 'deployment.zip.asc'

    gpg = gnupg.GPG(gnupghome=str(gpg_key['home']))

    with open(deployment_zip, 'rb') as f:
        signed = gpg.sign_file(
            f,
            keyid=gpg_key['key_id'],
            detach=True,
            output=str(deployment_sig)
        )

    if not signed:
        pytest.fail(f"GPG signing failed: {signed.stderr if hasattr(signed, 'stderr') else 'Unknown error'}")

    # Verify signature (sanity check using python-gnupg)
    with open(deployment_sig, 'rb') as sig_file:
        verified = gpg.verify_file(sig_file, str(deployment_zip))

    if not verified.valid:
        pytest.fail(f"GPG signature verification failed: {verified.status}")

    # Create wrapper (deployment_signed.zip)
    deployment_signed = temp_dirs['quarantine'] / 'deployment_signed.zip'
    with zipfile.ZipFile(deployment_signed, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(deployment_zip, 'deployment.zip')
        zf.write(deployment_sig, 'deployment.zip.asc')

    return {
        'deployment_zip': deployment_zip,
        'deployment_sig': deployment_sig,
        'deployment_signed': deployment_signed,
        'package_dir': pkg_dir,
        'files_dir': files_dir,
    }


@pytest.fixture
def watcher(temp_dirs: Dict[str, Path], gpg_key: Dict[str, any], monkeypatch):
    """
    Patch deployment-watcher paths to use temp directories and return the module.
    Returns the patched deployment_watcher module for testing.
    """
    # Use globally imported deployment_watcher module

    # Patch configuration constants
    monkeypatch.setattr(deployment_watcher, 'QUARANTINE_DIR', temp_dirs['quarantine'])
    monkeypatch.setattr(deployment_watcher, 'OUTPUTS_DIR', temp_dirs['outputs'])
    monkeypatch.setattr(deployment_watcher, 'DEPLOYMENT_DIR', temp_dirs['deployment'])
    monkeypatch.setattr(deployment_watcher, 'DEPLOYMENT_LOCK', temp_dirs['locks'] / 'deployment.lock')
    monkeypatch.setattr(deployment_watcher, 'GPG_HOME', gpg_key['home'])
    monkeypatch.setattr(deployment_watcher, 'LOG_FILE', temp_dirs['logs'] / 'deployment.log')

    # Reconfigure logging to use temp dir
    import logging

    # Remove existing handlers
    for handler in deployment_watcher.logger.handlers[:]:
        deployment_watcher.logger.removeHandler(handler)

    # Add new handlers with temp paths
    file_handler = logging.FileHandler(temp_dirs['logs'] / 'deployment.log')
    file_handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', '%Y-%m-%d %H:%M:%S'))
    deployment_watcher.logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', '%Y-%m-%d %H:%M:%S'))
    deployment_watcher.logger.addHandler(stream_handler)

    yield deployment_watcher

    # Cleanup handlers
    for handler in deployment_watcher.logger.handlers[:]:
        handler.close()
        deployment_watcher.logger.removeHandler(handler)


# ============================================================================
# DOCKER TEST SUPPORT
# ============================================================================

def pytest_addoption(parser):
    """Add command-line options for pytest."""
    parser.addoption(
        "--docker",
        action="store_true",
        default=False,
        help="Run Docker-based integration tests"
    )
    parser.addoption(
        "--no-docker-cleanup",
        action="store_true",
        default=False,
        help="Don't cleanup Docker containers after tests (for debugging)"
    )


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers",
        "docker: mark test to run only with Docker containers"
    )
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test"
    )


def pytest_collection_modifyitems(config, items):
    """Skip docker tests if --docker flag is not provided."""
    if not config.getoption("--docker"):
        skip_docker = pytest.mark.skip(reason="need --docker option to run")
        for item in items:
            if "docker" in item.keywords:
                item.add_marker(skip_docker)


@pytest.fixture(scope="session")
def docker_available():
    """Check if Docker is available."""
    try:
        import docker
        client = docker.from_env()
        client.ping()
        return True
    except Exception as e:
        logger.warning(f"Docker not available: {e}")
        return False


@pytest.fixture(scope="session")
def shared_docker_container(request):
    """Shared Docker container for deployment-watcher tests."""
    if not request.config.getoption("--docker", default=False):
        return None

    # Import from helpers subdirectory
    import sys
    from pathlib import Path
    test_dir = Path(__file__).parent
    if str(test_dir) not in sys.path:
        sys.path.insert(0, str(test_dir))

    from helpers.docker_test_helper import SystemdTestContainer

    logger.info("Creating shared Docker container for test session")
    container = SystemdTestContainer()

    try:
        container.build_image(show_output=True)
        container.start_container(show_output=True)
        logger.info(f"Docker container ready: {container.container_name}")
        yield container

    finally:
        if not request.config.getoption("--no-docker-cleanup", default=False):
            logger.info("Cleaning up Docker container after test session")
            container.cleanup()
        else:
            logger.info(f"Keeping Docker container for debugging: {container.container_name}")
