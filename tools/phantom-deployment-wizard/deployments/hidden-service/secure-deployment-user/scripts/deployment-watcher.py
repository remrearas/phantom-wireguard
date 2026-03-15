#!/usr/bin/env python3
# ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
# ██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
# ██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
# ██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
# ██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
# ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
# Copyright (c) 2025 Rıza Emre ARAS
#
# Deployment Watcher
#

import os
import sys
import logging
import subprocess
import zipfile
import shutil
import tempfile
import time
from pathlib import Path
from typing import Optional

# Check for required python-gnupg library at startup
import importlib.util

if importlib.util.find_spec("gnupg") is None:
    print("ERROR: python-gnupg is required. Install with: pip install python-gnupg", file=sys.stderr)
    sys.exit(1)

import gnupg

# ============================================================================
# CONFIGURATION
# ============================================================================

QUARANTINE_DIR = Path("/securepath/incoming")
OUTPUTS_DIR = Path("/securepath/outputs")
DEPLOYMENT_DIR = Path("/tmp/deployment")
DEPLOYMENT_LOCK = Path("/var/lock/deployment.lock")
GPG_HOME = Path("/opt/deployment-secrets/gpg")
LOG_FILE = Path("/var/log/deployment.log")
SIGNED_PACKAGE_NAME = "deployment_signed.zip"

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


# ============================================================================
# DEPLOYMENT LOCK
# ============================================================================

class DeploymentLock:
    """Simple file-based deployment lock"""

    def __init__(self, lock_file: Path):
        self.lock_file = lock_file
        self.locked = False

    def acquire(self) -> bool:
        """Try to acquire lock, return False if already locked"""
        if self.lock_file.exists():
            logger.error("✗ Deployment already in progress - REJECTING")
            return False

        try:
            self.lock_file.touch()
            self.locked = True
            logger.info("✓ Deployment lock acquired")
            return True
        except Exception as e:
            logger.error(f"Failed to acquire lock: {e}")
            return False

    def release(self):
        """Release lock"""
        if self.locked:
            try:
                self.lock_file.unlink(missing_ok=True)
                self.locked = False
                logger.info("✓ Deployment lock released")
            except Exception as e:
                logger.warning(f"Failed to release lock: {e}")


# ============================================================================
# WRAPPER VALIDATION
# ============================================================================

def wait_for_file_closed(file_path: Path, timeout: int = 30) -> bool:
    """
    Wait for file to be closed by checking if any process has it open using lsof.
    This prevents race conditions when SFTP uploads are still in progress.

    Args:
        file_path: Path to the file to check
        timeout: Maximum seconds to wait (default: 30)

    Returns:
        True if file is closed and ready, False if timeout
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            # lsof returns non-zero exit code if no process has the file open
            result = subprocess.run(
                ['lsof', str(file_path)],
                capture_output=True,
                text=True,
                timeout=5
            )

            # returncode != 0 means file is NOT open by any process
            if result.returncode != 0:
                logger.info("✓ File closed - upload complete")
                return True

            # File still open, log which process has it (for debugging)
            if result.stdout:
                logger.debug(f"File still open: {result.stdout.strip()}")

        except subprocess.TimeoutExpired:
            logger.warning("lsof command timeout")
        except FileNotFoundError:
            logger.error("lsof command not found - install lsof package")
            return False
        except Exception as e:
            logger.warning(f"lsof check error: {e}")

        time.sleep(0.5)  # Check every 500ms

    logger.error(f"✗ Timeout waiting for file to close ({timeout}s)")
    return False


def validate_wrapper_structure(wrapper_path: Path) -> bool:
    """Validate wrapper structure WITHOUT extracting"""

    # Wait for upload to complete (race condition prevention)
    if not wait_for_file_closed(wrapper_path, timeout=30):
        logger.error("✗ File upload incomplete or timeout")
        return False

    try:
        with zipfile.ZipFile(wrapper_path, 'r') as zf:
            files = set(zf.namelist())
            required = {'deployment.zip', 'deployment.zip.asc'}

            # Exact match
            if files != required:
                logger.error(f"✗ Invalid wrapper structure. Found: {files}, Expected: {required}")
                return False

            # Security: Path traversal check
            for name in files:
                if name.startswith('/') or '..' in name or name.startswith('..'):
                    logger.error(f"✗ Path traversal attempt: {name}")
                    return False

            # Optional: Check .asc file size
            for info in zf.infolist():
                if info.filename == 'deployment.zip.asc':
                    if info.file_size > 10 * 1024:  # 10KB
                        logger.error("✗ Signature file too large")
                        return False

            logger.info("✓ Wrapper structure valid")
            return True

    except zipfile.BadZipFile:
        logger.error("✗ Invalid or corrupt ZIP file")
        return False
    except Exception as e:
        logger.error(f"✗ Validation error: {e}")
        return False


# ============================================================================
# WRAPPER EXTRACTION
# ============================================================================

def extract_wrapper(wrapper_path: Path) -> Optional[Path]:
    """Extract wrapper to random tmp directory"""
    verify_dir: Optional[Path] = None
    try:
        verify_dir = Path(tempfile.mkdtemp(prefix='deployment-verify-'))
        logger.info(f"Created verify directory: {verify_dir}")

        with zipfile.ZipFile(wrapper_path, 'r') as zf:
            # Extract ONLY the 2 required files
            zf.extract('deployment.zip', verify_dir)
            zf.extract('deployment.zip.asc', verify_dir)

        logger.info("✓ Wrapper extracted")
        return verify_dir

    except Exception as e:
        logger.error(f"✗ Wrapper extraction failed: {e}")
        if verify_dir is not None:
            shutil.rmtree(verify_dir, ignore_errors=True)
        return None


# ============================================================================
# GPG VERIFICATION
# ============================================================================

def verify_gpg_signature(deployment_zip: Path, signature: Path) -> bool:
    """Verify GPG signature using python-gnupg library"""
    try:
        logger.info("Verifying GPG signature...")

        # Initialize GPG with isolated home directory
        gpg = gnupg.GPG(gnupghome=str(GPG_HOME))

        # Verify the detached signature
        with open(signature, 'rb') as sig_file:
            verified = gpg.verify_file(sig_file, str(deployment_zip))

        # Check verification status
        if verified.valid:
            logger.info(f"✓ GPG signature VALID (key: {verified.key_id})")
            return True
        else:
            logger.error("✗ GPG signature INVALID")
            logger.error(f"SECURITY ALERT: Invalid signature detected - Status: {verified.status}")
            if verified.stderr:
                logger.error(f"GPG Error: {verified.stderr}")
            return False

    except FileNotFoundError as e:
        logger.error(f"✗ File not found during GPG verification: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ GPG verification failed: {e}")
        return False


# ============================================================================
# DEPLOYMENT ZIP VALIDATION
# ============================================================================

def validate_deployment_zip(deployment_zip: Path) -> bool:
    """Validate deployment.zip structure WITHOUT extracting"""
    try:
        with zipfile.ZipFile(deployment_zip, 'r') as zf:
            files = zf.namelist()

            # Must contain run.sh
            if 'run.sh' not in files:
                logger.error("✗ Missing run.sh in deployment.zip")
                return False

            # Must contain files/ directory (check for any files/* entry)
            has_files_dir = any(f.startswith('files/') for f in files)
            if not has_files_dir:
                logger.error("✗ Missing files/ directory in deployment.zip")
                return False

            # Security: Path traversal check
            for name in files:
                if name.startswith('/') or '..' in name:
                    logger.error(f"✗ Path traversal attempt in deployment: {name}")
                    return False

                # Only allow run.sh and files/* paths
                if not (name == 'run.sh' or name.startswith('files/')):
                    logger.error(f"✗ Unauthorized file in deployment.zip: {name}")
                    return False

            logger.info("✓ Deployment.zip structure valid")
            return True

    except zipfile.BadZipFile:
        logger.error("✗ Invalid deployment.zip")
        return False
    except Exception as e:
        logger.error(f"✗ Deployment validation error: {e}")
        return False


# ============================================================================
# DEPLOYMENT EXTRACTION
# ============================================================================

def extract_deployment(deployment_zip: Path, destination: Path) -> bool:
    """Extract deployment.zip to destination"""
    try:
        logger.info(f"Extracting deployment to {destination}...")

        # Create destination directory
        destination.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(deployment_zip, 'r') as zf:
            # Extract run.sh
            zf.extract('run.sh', destination)

            # Extract files/ directory (all files inside it)
            for member in zf.namelist():
                if member.startswith('files/'):
                    zf.extract(member, destination)

        logger.info("✓ Deployment extracted")
        return True

    except zipfile.BadZipFile:
        logger.error("✗ Invalid deployment.zip")
        return False
    except Exception as e:
        logger.error(f"✗ Deployment extraction failed: {e}")
        return False


# ============================================================================
# PERMISSIONS
# ============================================================================

def set_deployment_permissions(deployment_dir: Path):
    """Set proper permissions for deployment"""
    try:
        for item in deployment_dir.rglob('*'):
            shutil.chown(item, user='root', group='root')
            if item.is_file():
                item.chmod(0o644)
            elif item.is_dir():
                item.chmod(0o755)

        logger.info("✓ Permissions set")
    except Exception as e:
        logger.warning(f"Permission change failed: {e}")


# ============================================================================
# EXECUTION
# ============================================================================

def execute_deployment_script(deployment_dir: Path) -> bool:
    """Execute deployment script"""
    try:
        # Set environment variables
        env = os.environ.copy()
        env['DEPLOYMENT_ROOT'] = str(deployment_dir)
        env['DEPLOYMENT_FILES'] = str(deployment_dir / 'files')

        run_script = deployment_dir / 'run.sh'

        # Make run.sh executable
        run_script.chmod(0o755)
        logger.info("✓ run.sh made executable")

        logger.info("Executing deployment script...")
        logger.info("=" * 60)

        # Execute deployment script run.sh with real-time output logging
        process = subprocess.Popen(
            ['./run.sh'],
            cwd=deployment_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Merge stderr into stdout
            text=True,
            bufsize=1,  # Line buffered
            universal_newlines=True
        )

        # Log output in real-time (automatically goes to deployment.txt via FileHandler)
        try:
            for line in process.stdout:
                line = line.rstrip()
                if line:  # Skip empty lines
                    logger.info(f"[run.sh] {line}")

            # Wait for process to complete
            returncode = process.wait(timeout=600)  # 10 minute timeout

        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            logger.error("✗ Deployment timeout (>10 minutes)")
            return False

        logger.info("=" * 60)

        # Log final result
        if returncode == 0:
            logger.info("✓ Deployment completed successfully")
            return True
        else:
            logger.error(f"✗ Deployment failed (exit code: {returncode})")
            return False

    except FileNotFoundError:
        logger.error("✗ Deployment script not found")
        return False
    except Exception as e:
        logger.error(f"✗ Deployment script execution failed: {e}")
        return False


# ============================================================================
# MAIN DEPLOYMENT PROCESS
# ============================================================================

def process_deployment():
    """Main deployment processing function"""

    logger.info("Deployment watcher started")

    # Step 1: Check for signed package
    signed_package = QUARANTINE_DIR / SIGNED_PACKAGE_NAME
    if not signed_package.exists():
        logger.info("No deployment package found")
        return

    logger.info(f"Found signed package: {signed_package.name}")

    # Step 2: Check lock
    lock = DeploymentLock(DEPLOYMENT_LOCK)
    if not lock.acquire():
        logger.error(f"Rejecting package: {signed_package.name}")
        signed_package.unlink(missing_ok=True)
        return

    # Step 3: Create deployment output file for CI/CD monitoring
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUTS_DIR / "deployment.txt"

    # Add file handler to logger for this deployment (all logs go to deployment.txt)
    deployment_handler = logging.FileHandler(output_file, mode='w')
    deployment_handler.setLevel(logging.INFO)
    deployment_handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    logger.addHandler(deployment_handler)

    logger.info("✓ Created deployment.txt for CI/CD monitoring")

    # Step 4: Clean deployment directory (fresh start)
    if DEPLOYMENT_DIR.exists():
        shutil.rmtree(DEPLOYMENT_DIR, ignore_errors=True)
        logger.info("✓ Deployment directory cleaned (fresh start)")

    verify_dir = None

    try:
        # Step 4: Validate wrapper structure
        if not validate_wrapper_structure(signed_package):
            logger.error("Invalid wrapper - DELETING")
            return

        # Step 5: Extract wrapper
        verify_dir = extract_wrapper(signed_package)
        if not verify_dir:
            return

        # Step 6: Verify GPG signature
        deployment_zip = verify_dir / 'deployment.zip'
        signature = verify_dir / 'deployment.zip.asc'

        if not verify_gpg_signature(deployment_zip, signature):
            return

        # Step 7: Validate deployment.zip structure
        if not validate_deployment_zip(deployment_zip):
            return

        # Step 8: Extract deployment
        if not extract_deployment(deployment_zip, DEPLOYMENT_DIR):
            return

        # Step 9: Set permissions
        set_deployment_permissions(DEPLOYMENT_DIR)

        # Step 10: Execute deployment script
        if execute_deployment_script(DEPLOYMENT_DIR):
            logger.info("✓ Deployment completed successfully")
        else:
            logger.error("✗ Deployment failed")

    except Exception as e:
        logger.error(f"Unexpected error: {e}")

    finally:
        # Cleanup
        if verify_dir and verify_dir.exists():
            shutil.rmtree(verify_dir, ignore_errors=True)
            logger.info("✓ Verify directory cleaned")

        signed_package.unlink(missing_ok=True)
        logger.info("✓ Signed package removed")

        lock.release()
        logger.info("Deployment watcher completed")
        logger.info("-" * 60)

        # Remove deployment handler and delete deployment.txt (CI/CD signals completion by file deletion)
        deployment_handler.flush()  # Ensure all buffered logs are written to disk
        time.sleep(3)  # Give monitor.py time to read final logs before deletion
        logger.removeHandler(deployment_handler)
        deployment_handler.close()
        output_file.unlink(missing_ok=True)
        logger.info("✓ deployment.txt removed (CI/CD completion signal)")


# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    """Main entry point"""
    try:
        # Check if running as root
        if os.geteuid() != 0:
            logger.error("This script must be run as root")
            sys.exit(1)

        # Run deployment process
        process_deployment()

    except KeyboardInterrupt:
        logger.info("Watcher interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
