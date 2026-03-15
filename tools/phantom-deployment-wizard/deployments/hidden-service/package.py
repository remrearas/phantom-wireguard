# ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
# ██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
# ██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
# ██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
# ██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
# ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
# Copyright (c) 2025 Rıza Emre ARAS

import os
import sys
import logging
import tempfile
import zipfile
import shutil
from pathlib import Path
import gnupg

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Configuration
SCRIPT_DIR = Path(__file__).parent.resolve()
PHANTOM_WIZARD_ROOT = SCRIPT_DIR.parent.parent  # Go up to phantom-deployment-wizard/
OUTPUT_DIR = SCRIPT_DIR / "build"


def error_exit(message):
    """Log error and exit"""
    logger.error(message)
    sys.exit(1)


def print_header():
    """Print script header"""
    print("██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗")
    print("██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║")
    print("██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║")
    print("██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║")
    print("██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║")
    print("╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝")
    print("Phantom Deployment Wizard - Deployment Package Creator")
    print("Copyright (c) 2025 Rıza Emre ARAS")


def copy_project_files(temp_dir):
    """Copy phantom-deployment-wizard files to temp directory (excluding deployments/)"""
    logger.info("Copying project files...")

    files_dir = temp_dir / "files"
    files_dir.mkdir(parents=True, exist_ok=True)

    # Directories and files to exclude
    exclude_dirs = {'deployments', '__pycache__', '.git', '.pytest_cache', 'build', '.venv', 'venv'}
    exclude_files = {'.DS_Store', '.gitignore', '*.pyc'}

    copied_count = 0

    # Walk through phantom-deployment-wizard directory
    for root, dirs, files in os.walk(PHANTOM_WIZARD_ROOT):
        root_path = Path(root)

        # Skip if current directory is in exclude list
        if any(excluded in root_path.parts for excluded in exclude_dirs):
            continue

        # Remove excluded directories from dirs list to prevent walking into them
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            # Skip excluded files
            if file in exclude_files or file.endswith('.pyc'):
                continue

            src_file = root_path / file

            # Calculate relative path from PHANTOM_WIZARD_ROOT
            try:
                rel_path = src_file.relative_to(PHANTOM_WIZARD_ROOT)
            except ValueError:
                continue

            # Destination in files/ directory
            dst_file = files_dir / rel_path
            dst_file.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            shutil.copy2(src_file, dst_file)
            copied_count += 1

    logger.info(f"Copied {copied_count} files to deployment package")
    return files_dir


def read_gpg_key_from_stdin():
    """Read GPG private key from stdin"""
    logger.info("Reading GPG private key from stdin...")

    if sys.stdin.isatty():
        error_exit("GPG private key must be provided via stdin (pipe or redirect)")

    gpg_key = sys.stdin.read().strip()

    if not gpg_key:
        error_exit("No GPG private key provided")

    if "BEGIN PGP PRIVATE KEY BLOCK" not in gpg_key:
        error_exit("Invalid GPG private key format")

    logger.info("GPG private key read successfully")
    return gpg_key


def validate_and_import_gpg_key(gpg_key, gpg_home):
    """Validate and import GPG private key"""
    logger.info("Validating GPG private key...")

    # Initialize GPG with isolated home directory
    gpg = gnupg.GPG(gnupghome=str(gpg_home))

    # Import the private key
    import_result = gpg.import_keys(gpg_key)

    if import_result.count == 0:
        error_exit("Failed to import GPG private key")

    if not import_result.fingerprints:
        error_exit("No valid GPG key fingerprints found")

    key_id = import_result.fingerprints[0]
    logger.info(f"GPG private key imported successfully: {key_id}")

    return gpg, key_id


def validate_deployment_zip_structure(deployment_zip):
    """Validate inner deployment.zip structure"""
    try:
        with zipfile.ZipFile(deployment_zip, 'r') as zf:
            files = zf.namelist()

            # Must contain run.sh
            if 'run.sh' not in files:
                logger.error("Missing run.sh in deployment.zip")
                return False

            # Must contain files/ directory
            has_files_dir = any(f.startswith('files/') for f in files)
            if not has_files_dir:
                logger.error("Missing files/ directory in deployment.zip")
                return False

            logger.info("Deployment.zip structure validated")
            return True

    except zipfile.BadZipFile as e:
        logger.error(f"Inner deployment.zip is corrupted: {e}")
        return False
    except Exception as e:
        logger.error(f"Deployment.zip validation error: {e}")
        return False


def create_deployment_zip(temp_dir, files_dir):
    """Create deployment.zip with run.sh and files/"""
    logger.info("Creating deployment.zip...")

    deployment_zip = temp_dir / "deployment.zip"

    # Read run.sh from deployments/hidden-service/
    run_script_source = SCRIPT_DIR / "run.sh"
    if not run_script_source.exists():
        error_exit(f"run.sh not found: {run_script_source}")

    # Create zip archive
    with zipfile.ZipFile(deployment_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add run.sh
        zf.write(run_script_source, 'run.sh')
        logger.info("Added run.sh to package")

        # Add all files from files/ directory
        file_count = 0
        for file_path in files_dir.rglob('*'):
            if file_path.is_file():
                arcname = f"files/{file_path.relative_to(files_dir)}"
                zf.write(file_path, arcname)
                file_count += 1

        logger.info(f"Added {file_count} files to package")

    logger.info(f"Created deployment.zip: {deployment_zip.stat().st_size / 1024:.1f} KB")

    # Validate the created deployment.zip
    if not validate_deployment_zip_structure(deployment_zip):
        error_exit("Deployment.zip validation failed")

    return deployment_zip


def sign_deployment_zip(gpg, key_id, deployment_zip, output_dir):
    """Sign deployment.zip with GPG"""
    logger.info("Signing deployment.zip with GPG...")

    signature_file = output_dir / "deployment.zip.asc"

    # Sign the deployment.zip
    with open(deployment_zip, 'rb') as f:
        signed = gpg.sign_file(
            f,
            keyid=key_id,
            detach=True,
            output=str(signature_file)
        )

    if not signed:
        error_exit(f"Failed to sign deployment.zip: {signed.stderr if hasattr(signed, 'stderr') else 'Unknown error'}")

    logger.info(f"Signature created: {signature_file.stat().st_size} bytes")
    return signature_file


def validate_wrapper_structure(wrapper_path):
    """Validate wrapper ZIP structure matches deployment-watcher expectations"""
    try:
        with zipfile.ZipFile(wrapper_path, 'r') as zf:
            files = set(zf.namelist())
            required = {'deployment.zip', 'deployment.zip.asc'}

            if files != required:
                logger.error(f"Wrapper validation failed. Found: {files}, Expected: {required}")
                return False

            logger.info("Wrapper structure validated")
            return True

    except zipfile.BadZipFile as e:
        logger.error(f"Wrapper is corrupted: {e}")
        return False
    except Exception as e:
        logger.error(f"Wrapper validation error: {e}")
        return False


def create_signed_wrapper(deployment_zip, signature_file, output_dir):
    """Create deployment_signed.zip wrapper"""
    logger.info("Creating deployment_signed.zip wrapper...")

    wrapper_file = output_dir / "deployment_signed.zip"

    with zipfile.ZipFile(wrapper_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(deployment_zip, 'deployment.zip')
        zf.write(signature_file, 'deployment.zip.asc')

    logger.info(f"Wrapper created: {wrapper_file.stat().st_size / 1024:.1f} KB")

    # Validate wrapper structure immediately
    if not validate_wrapper_structure(wrapper_file):
        error_exit("Wrapper validation failed - aborting")

    return wrapper_file


def main():
    """Main function"""
    print_header()

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Create temporary working directory
    temp_dir = Path(tempfile.mkdtemp(prefix='phantom-deploy-'))

    # Create temporary GPG home directory
    gpg_home = Path(tempfile.mkdtemp(prefix='gpg-deploy-'))
    gpg_home.chmod(0o700)

    try:
        logger.info("Starting deployment package creation...")

        # Step 1: Read and validate GPG private key from stdin
        gpg_key = read_gpg_key_from_stdin()
        gpg, key_id = validate_and_import_gpg_key(gpg_key, gpg_home)

        # Step 2: Copy project files (excluding deployments/)
        files_dir = copy_project_files(temp_dir)

        # Step 3: Create deployment.zip
        deployment_zip = create_deployment_zip(temp_dir, files_dir)

        # Step 4: Sign deployment.zip
        signature_file = sign_deployment_zip(gpg, key_id, deployment_zip, temp_dir)

        # Step 5: Create deployment_signed.zip wrapper
        wrapper_file_temp = create_signed_wrapper(deployment_zip, signature_file, temp_dir)

        # Step 6: Copy only deployment_signed.zip to output directory
        final_wrapper = OUTPUT_DIR / "deployment_signed.zip"
        shutil.copy2(wrapper_file_temp, final_wrapper)

        logger.info("Deployment package created successfully")
        logger.info(f"Output: {final_wrapper}")
        logger.info(f"Size: {final_wrapper.stat().st_size / 1024:.1f} KB")

    except Exception as e:
        error_exit(f"Failed to create deployment package: {e}")
    finally:
        # Cleanup temporary directories
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        if gpg_home.exists():
            shutil.rmtree(gpg_home, ignore_errors=True)


if __name__ == "__main__":
    main()
