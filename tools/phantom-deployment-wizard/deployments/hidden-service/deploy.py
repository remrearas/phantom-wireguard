# ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
# ██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
# ██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
# ██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
# ██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
# ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
# Copyright (c) 2025 Rıza Emre ARAS

import sys
import time
import argparse
import logging
from pathlib import Path

import importlib.util

if importlib.util.find_spec("paramiko") is None:
    print("ERROR: paramiko is required. Install with: pip install paramiko", file=sys.stderr)
    sys.exit(1)

import paramiko

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)

logger = logging.getLogger(__name__)


# ============================================================================
# SFTP CONNECTION
# ============================================================================

def create_sftp_client(server_ip: str, ssh_port: int, ssh_user: str, ssh_key: str):
    """Create SFTP client connection"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        logger.info(f"Connecting to {ssh_user}@{server_ip}:{ssh_port}...")

        ssh.connect(
            hostname=server_ip,
            port=ssh_port,
            username=ssh_user,
            key_filename=ssh_key,
            timeout=10
        )

        sftp = ssh.open_sftp()
        logger.info("SFTP connection established")

        return ssh, sftp

    except Exception as e:
        logger.error(f"Failed to connect: {e}")
        sys.exit(1)


# ============================================================================
# DEPLOYMENT UPLOAD
# ============================================================================

def upload_deployment_package(sftp, local_package: str, remote_dir: str = 'incoming'):
    """Upload deployment package to server"""
    try:
        local_path = Path(local_package)

        # Validate local package exists
        if not local_path.exists():
            logger.error(f"Deployment package not found: {local_path}")
            return False

        # Remote path (chroot-aware)
        remote_path = f"{remote_dir}/deployment_signed.zip"

        logger.info(f"Uploading {local_path.name} to {remote_path}...")

        # Upload with progress
        file_size = local_path.stat().st_size
        logger.info(f"Package size: {file_size / 1024 / 1024:.2f} MB")

        sftp.put(str(local_path), remote_path)

        logger.info("Upload completed successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to upload deployment package: {e}")
        return False


# ============================================================================
# DEPLOYMENT MONITORING
# ============================================================================

def wait_for_deployment_start(sftp, deployment_file: str, timeout: int = 300):
    """Wait for deployment.txt to be created"""
    logger.info(f"Waiting for deployment to start (timeout: {timeout}s)...")

    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            sftp.stat(deployment_file)
            print("")  # New line after dots
            logger.info("Deployment started")
            print("")  # Empty line before logs
            return True
        except FileNotFoundError:
            time.sleep(2)
            print(".", end="", flush=True)

    print("")  # New line after dots
    logger.error(f"Timeout: deployment.txt not created within {timeout}s")
    return False


def monitor_deployment_logs(sftp, deployment_file: str, poll_interval: int = 2):
    """Monitor deployment.txt in real-time"""
    print("=" * 80)
    print("DEPLOYMENT LOGS")
    print("=" * 80)
    print("")

    last_position = 0

    while True:
        try:
            # Read file from last position
            with sftp.file(deployment_file, 'r') as f:
                f.seek(last_position)
                new_content = f.read().decode('utf-8', errors='replace')

                if new_content:
                    # Split into lines and print each line cleanly
                    for line in new_content.splitlines():
                        # Print each line as-is (preserves original formatting)
                        print(line)
                        sys.stdout.flush()

                    # Update position
                    last_position = f.tell()

            # Poll interval
            time.sleep(poll_interval)

        except FileNotFoundError:
            # File deleted = deployment completed
            print("")
            print("=" * 80)
            print("Deployment process completed")
            print("=" * 80)
            return 0

        except Exception as e:
            print("")
            print("=" * 80)
            print(f"Error reading deployment logs: {e}")
            print("=" * 80)
            return 1


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Deploy Phantom Hidden Service')

    parser.add_argument('--server-ip', required=True,
                        help='Server IP address or hostname')
    parser.add_argument('--ssh-port', type=int, default=22,
                        help='SSH port (default: 22)')
    parser.add_argument('--ssh-user', required=True,
                        help='SSH username (deployment-user)')
    parser.add_argument('--ssh-key', required=True,
                        help='Path to SSH private key')
    parser.add_argument('--package', default='build/deployment_signed.zip',
                        help='Path to deployment package (default: build/deployment_signed.zip)')
    parser.add_argument('--deployment-file', default='outputs/deployment.txt',
                        help='Path to deployment log file (default: outputs/deployment.txt)')
    parser.add_argument('--wait-timeout', type=int, default=300,
                        help='Timeout for deployment start (default: 300s)')
    parser.add_argument('--poll-interval', type=int, default=2,
                        help='Log polling interval in seconds (default: 2)')

    args = parser.parse_args()

    # Validate SSH key
    ssh_key_path = Path(args.ssh_key).expanduser()
    if not ssh_key_path.exists():
        logger.error(f"SSH key not found: {ssh_key_path}")
        sys.exit(1)

    # Validate package path
    package_path = Path(args.package)
    if not package_path.exists():
        logger.error(f"Deployment package not found: {package_path}")
        sys.exit(1)

    try:
        # Connect via SFTP
        ssh, sftp = create_sftp_client(
            args.server_ip,
            args.ssh_port,
            args.ssh_user,
            str(ssh_key_path)
        )

        # Upload deployment package
        if not upload_deployment_package(sftp, str(package_path)):
            sftp.close()
            ssh.close()
            sys.exit(1)

        print("")  # Empty line after upload

        # Wait for deployment to start
        if not wait_for_deployment_start(sftp, args.deployment_file, args.wait_timeout):
            sftp.close()
            ssh.close()
            sys.exit(1)

        # Monitor logs in real-time
        exit_code = monitor_deployment_logs(sftp, args.deployment_file, args.poll_interval)

        sftp.close()
        ssh.close()
        sys.exit(exit_code)

    except KeyboardInterrupt:
        print("")
        print("")
        logger.info("Deployment interrupted by user")
        sys.exit(130)
    except Exception as e:
        print("")
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
