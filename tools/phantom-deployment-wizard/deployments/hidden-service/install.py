# ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
# ██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
# ██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
# ██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
# ██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
# ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
# Copyright (c) 2025 Rıza Emre ARAS

import os
import sys
import argparse
import tempfile
import zipfile
import shutil
import logging
from pathlib import Path
from textwrap import dedent
import gnupg
import paramiko

# Configuration
SCRIPT_DIR = Path(__file__).parent.resolve()
SECURE_DEPLOYMENT_DIR = SCRIPT_DIR / "secure-deployment-user"
INSTALLATION_FLAG = "/opt/secure-deployment-user/.installed"
OUTPUT_DIR = SCRIPT_DIR / "output"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


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
    print("Phantom Deployment Wizard - Hidden Service Initial Setup")
    print("Copyright (c) 2025 Rıza Emre ARAS")


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Install secure-deployment-user system on remote server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=dedent("""
            Examples:
              Fresh installation:
                %(prog)s 192.168.1.100

              Custom SSH settings:
                %(prog)s 192.168.1.100 -u admin -p 2222 -k ~/.ssh/mykey

            This script will:
              1. Check if installation already exists
              2. Generate GPG key pair for deployment verification
              3. Install Docker on the server
              4. Deploy secure-deployment-user system
              5. Configure deployment user with AppArmor, chroot, and GPG verification
              6. Save all credentials to output/ directory
        """)
    )

    parser.add_argument('server_ip', help='Server IP address')
    parser.add_argument('-p', '--port', type=int, default=22, help='SSH port (default: 22)')
    parser.add_argument('-u', '--user', default='root', help='SSH username (default: root)')
    parser.add_argument('-k', '--key', default='~/.ssh/id_ed25519',
                        help='SSH private key path (default: ~/.ssh/id_ed25519)')

    return parser.parse_args()


def expand_path(path):
    """Expand user home directory in path"""
    return os.path.expanduser(path)


def create_ssh_client(server_ip, ssh_port, ssh_user, ssh_key):
    """Create and return configured SSH client"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    pkey = None
    try:
        pkey = paramiko.Ed25519Key.from_private_key_file(ssh_key)
    except (paramiko.SSHException, IOError, ValueError):
        try:
            pkey = paramiko.RSAKey.from_private_key_file(ssh_key)
        except (paramiko.SSHException, IOError, ValueError):
            error_exit(f"Could not load SSH key: {ssh_key}")

    try:
        client.connect(
            hostname=server_ip,
            port=ssh_port,
            username=ssh_user,
            pkey=pkey,
            timeout=10,
            allow_agent=False,
            look_for_keys=False
        )
        return client
    except (paramiko.SSHException, paramiko.AuthenticationException, IOError) as e:
        error_exit(f"SSH connection failed: {e}")


def exec_command(client, command):
    """Execute command on SSH client and return stdout, stderr, exit_code"""
    stdin, stdout, stderr = client.exec_command(command)
    exit_code = stdout.channel.recv_exit_status()
    return stdout.read().decode('utf-8'), stderr.read().decode('utf-8'), exit_code


def transfer_file(client, local_path, remote_path):
    """Transfer file using SFTP"""
    sftp = client.open_sftp()
    try:
        sftp.put(str(local_path), remote_path)
    finally:
        sftp.close()


def check_ssh_key(key_path):
    """Verify SSH key exists"""
    if not os.path.isfile(key_path):
        error_exit(f"SSH key not found: {key_path}")
    logger.info(f"SSH key found: {key_path}")


def test_ssh_connection(server_ip, ssh_port, ssh_user, ssh_key):
    """Test SSH connection to server"""
    logger.info(f"Testing SSH connection to {ssh_user}@{server_ip}:{ssh_port}...")

    client = create_ssh_client(server_ip, ssh_port, ssh_user, ssh_key)
    client.close()
    logger.info("SSH connection successful")


def check_installation_flag(server_ip, ssh_port, ssh_user, ssh_key):
    """Check if installation already exists"""
    logger.info("Checking for existing installation...")

    client = create_ssh_client(server_ip, ssh_port, ssh_user, ssh_key)
    try:
        stdout, stderr, exit_code = exec_command(client,
                                                 f'[ -f {INSTALLATION_FLAG} ] && echo "EXISTS" || echo "NOT_FOUND"')

        if "EXISTS" in stdout:
            logger.warning("Installation already exists on server")
            logger.warning(f"Installation flag found: {INSTALLATION_FLAG}")
            logger.warning("If you want to reinstall, remove the flag file first:")
            print(f"  ssh -p {ssh_port} -i {ssh_key} {ssh_user}@{server_ip} 'rm {INSTALLATION_FLAG}'")
            sys.exit(0)

        logger.info("No existing installation found, proceeding...")
    finally:
        client.close()


def generate_gpg_keypair():
    """Generate GPG key pair for deployment verification"""
    logger.info("Generating GPG key pair...")

    # Create temporary GPG home
    temp_gpg_home = tempfile.mkdtemp(prefix='gpg-keygen-')
    os.chmod(temp_gpg_home, 0o700)

    gpg = gnupg.GPG(gnupghome=temp_gpg_home)

    # Generate key
    input_data = gpg.gen_key_input(
        **{
            'name_real': 'Phantom Deployment Key',
            'name_email': 'deployment@deployment.local',
            'key_type': 'RSA',
            'key_length': 4096,
            'passphrase': '',
            'no_protection': True
        }
    )

    key = gpg.gen_key(input_data)

    if not key:
        shutil.rmtree(temp_gpg_home, ignore_errors=True)
        error_exit("GPG key generation failed")

    logger.info(f"GPG key generated: {key}")

    # Export public key
    public_key = gpg.export_keys(str(key))

    # Export private key (passphrase='' needed for GnuPG >= 2.1)
    private_key = gpg.export_keys(str(key), secret=True, passphrase='')

    # Save to temporary files
    public_key_file = Path(temp_gpg_home) / "deployment.asc"
    private_key_file = Path(temp_gpg_home) / "deployment-private.asc"

    public_key_file.write_text(public_key)
    private_key_file.write_text(private_key)

    logger.info("GPG keys exported")

    return temp_gpg_home, public_key_file, private_key_file, private_key


def check_server_os(server_ip, ssh_port, ssh_user, ssh_key):
    """Check server OS"""
    logger.info("Checking server OS...")

    client = create_ssh_client(server_ip, ssh_port, ssh_user, ssh_key)
    try:
        stdout, stderr, exit_code = exec_command(client, 'cat /etc/os-release | grep "^NAME=" | cut -d\\" -f2')
        os_info = stdout.strip()

        if "Debian" not in os_info and "Ubuntu" not in os_info:
            error_exit(f"Server must be running Debian/Ubuntu. Found: {os_info}")

        logger.info(f"Server OS: {os_info}")
    finally:
        client.close()


def update_system_packages(server_ip, ssh_port, ssh_user, ssh_key):
    """Update system packages"""
    logger.info("Updating system packages...")

    client = create_ssh_client(server_ip, ssh_port, ssh_user, ssh_key)
    try:
        stdout, stderr, exit_code = exec_command(client, 'apt-get update -qq')
        if exit_code != 0:
            error_exit(f"Failed to update packages: {stderr}")
        logger.info("System packages updated")
    finally:
        client.close()


def install_docker(server_ip, ssh_port, ssh_user, ssh_key):
    """Install Docker on server"""
    logger.info("Checking Docker installation...")

    client = create_ssh_client(server_ip, ssh_port, ssh_user, ssh_key)
    try:
        stdout, stderr, exit_code = exec_command(client, 'docker --version')

        if exit_code == 0:
            logger.info("Docker is already installed")
            return

        logger.info("Installing Docker...")
        stdout, stderr, exit_code = exec_command(
            client,
            'curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh && rm -f get-docker.sh'
        )

        if exit_code != 0:
            error_exit(f"Docker installation failed: {stderr}")

        logger.info("Docker installed successfully")
    finally:
        client.close()


def create_deployment_package():
    """Create secure-deployment-user package"""
    logger.info("Creating deployment package...")

    if not SECURE_DEPLOYMENT_DIR.exists():
        error_exit(f"secure-deployment-user directory not found: {SECURE_DEPLOYMENT_DIR}")

    # Create temporary directory
    temp_dir = tempfile.mkdtemp(prefix='deployment-package-')
    package_path = Path(temp_dir) / "secure-deployment-user.zip"

    # Create zip file
    with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(SECURE_DEPLOYMENT_DIR):
            # Skip __pycache__, tests and other unnecessary directories
            dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'tests']]

            for file in files:
                if file.endswith(('.pyc', '.DS_Store')):
                    continue

                file_path = Path(root) / file
                arcname = file_path.relative_to(SECURE_DEPLOYMENT_DIR.parent)
                zipf.write(file_path, arcname)

    logger.info(f"Package created: {package_path.stat().st_size / 1024:.1f} KB")

    return temp_dir, package_path


def deploy_to_server(server_ip, ssh_port, ssh_user, ssh_key, package_path, gpg_public_key_file):
    """Deploy package and GPG key to server"""
    logger.info("Transferring files to server...")

    client = create_ssh_client(server_ip, ssh_port, ssh_user, ssh_key)
    try:
        # Check and install unzip on server if needed
        exec_command(client, 'which unzip || apt-get install -y unzip')

        # Transfer files using SFTP
        transfer_file(client, package_path, '/tmp/secure-deployment-user.zip')
        transfer_file(client, gpg_public_key_file, '/tmp/deployment.asc')

        logger.info("Files transferred successfully")
    finally:
        client.close()


def extract_and_setup(server_ip, ssh_port, ssh_user, ssh_key):
    """Extract package and setup on server to /opt/secure-deployment-user"""
    logger.info("Extracting package to /opt/secure-deployment-user...")

    client = create_ssh_client(server_ip, ssh_port, ssh_user, ssh_key)
    try:
        # Create /opt directory if not exists and extract there
        stdout, stderr, exit_code = exec_command(
            client,
            'mkdir -p /opt && cd /opt && unzip -q -o /tmp/secure-deployment-user.zip && chmod +x /opt/secure-deployment-user/*.sh'
        )

        if exit_code != 0:
            error_exit(f"Failed to extract package: {stderr}")

        logger.info("Package extracted to /opt/secure-deployment-user and permissions set")
    finally:
        client.close()


def run_create_script(server_ip, ssh_port, ssh_user, ssh_key):
    """Run create.sh on server"""
    logger.info("Running create.sh on server...")
    logger.info("This will install secure-deployment-user system...")

    client = create_ssh_client(server_ip, ssh_port, ssh_user, ssh_key)
    try:
        stdout, stderr, exit_code = exec_command(
            client,
            'cd /opt/secure-deployment-user && ./create.sh --gpg-pubkey /tmp/deployment.asc'
        )

        if exit_code != 0:
            logger.error("create.sh failed")
            logger.error("STDOUT:")
            print(stdout)
            logger.error("STDERR:")
            print(stderr)
            error_exit("Installation failed")

        logger.info("create.sh completed successfully")
        return stdout
    finally:
        client.close()


def get_ssh_private_key(server_ip, ssh_port, ssh_user, ssh_key):
    """Retrieve SSH private key from server"""
    logger.info("Retrieving SSH private key...")

    client = create_ssh_client(server_ip, ssh_port, ssh_user, ssh_key)
    try:
        stdout, stderr, exit_code = exec_command(client, 'cat /home/deployment-user/.ssh/id_ed25519')

        if exit_code != 0:
            error_exit("Failed to retrieve SSH private key")

        logger.info("SSH private key retrieved")
        return stdout
    finally:
        client.close()


def create_installation_flag(server_ip, ssh_port, ssh_user, ssh_key):
    """Create installation flag on server"""
    logger.info("Creating installation flag...")

    client = create_ssh_client(server_ip, ssh_port, ssh_user, ssh_key)
    try:
        stdout, stderr, exit_code = exec_command(
            client,
            f'mkdir -p $(dirname {INSTALLATION_FLAG}) && touch {INSTALLATION_FLAG}'
        )

        if exit_code != 0:
            error_exit(f"Failed to create installation flag: {stderr}")

        logger.info(f"Installation flag created: {INSTALLATION_FLAG}")
    finally:
        client.close()


def restart_ssh_service(server_ip, ssh_port, ssh_user, ssh_key):
    """Restart SSH service to apply hardening configuration"""
    logger.info("Restarting SSH service...")

    client = create_ssh_client(server_ip, ssh_port, ssh_user, ssh_key)
    try:
        stdout, stderr, exit_code = exec_command(
            client,
            'systemctl restart sshd || systemctl restart ssh'
        )

        if exit_code != 0:
            logger.warning(f"Failed to restart SSH service: {stderr}")
        else:
            logger.info("SSH service restarted successfully")
    finally:
        client.close()


def cleanup_server_temp_files(server_ip, ssh_port, ssh_user, ssh_key):
    """Clean up temporary files from /tmp after installation"""
    logger.info("Cleaning up temporary files...")

    client = create_ssh_client(server_ip, ssh_port, ssh_user, ssh_key)
    try:
        stdout, stderr, exit_code = exec_command(
            client,
            'rm -f /tmp/secure-deployment-user.zip /tmp/deployment.asc'
        )

        if exit_code != 0:
            logger.warning(f"Failed to clean up some temporary files: {stderr}")
        else:
            logger.info("Temporary files cleaned up")
    finally:
        client.close()


def save_output(gpg_private_key, ssh_private_key):
    """Save keys to separate files"""
    # Create output directory if not exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Save GPG private key
    gpg_key_file = OUTPUT_DIR / "gpg_private_key.asc"
    gpg_key_file.write_text(gpg_private_key)
    logger.info(f"GPG private key saved: {gpg_key_file}")

    # Save SSH private key
    ssh_key_file = OUTPUT_DIR / "ssh_private_key"
    ssh_key_file.write_text(ssh_private_key)
    logger.info(f"SSH private key saved: {ssh_key_file}")

    return OUTPUT_DIR


def cleanup_temp_directories(temp_dirs):
    """Clean up temporary directories"""
    for temp_dir in temp_dirs:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    """Main function"""
    print_header()

    # Parse arguments
    args = parse_arguments()

    server_ip = args.server_ip
    ssh_port = args.port
    ssh_user = args.user
    ssh_key = expand_path(args.key)

    logger.info(f"Target server: {ssh_user}@{server_ip}:{ssh_port}")
    logger.info(f"SSH key: {ssh_key}")

    # Track temporary directories for cleanup
    temp_dirs = []

    try:
        # Validate SSH key
        check_ssh_key(ssh_key)

        # Test SSH connection
        test_ssh_connection(server_ip, ssh_port, ssh_user, ssh_key)

        # Check installation flag
        check_installation_flag(server_ip, ssh_port, ssh_user, ssh_key)

        # Check server OS
        check_server_os(server_ip, ssh_port, ssh_user, ssh_key)

        # Generate GPG keypair
        gpg_temp_dir, gpg_public_key_file, gpg_private_key_file, gpg_private_key = generate_gpg_keypair()
        temp_dirs.append(gpg_temp_dir)

        # Update system packages
        update_system_packages(server_ip, ssh_port, ssh_user, ssh_key)

        # Install Docker
        install_docker(server_ip, ssh_port, ssh_user, ssh_key)

        # Create deployment package
        package_temp_dir, package_path = create_deployment_package()
        temp_dirs.append(package_temp_dir)

        # Deploy to server
        deploy_to_server(server_ip, ssh_port, ssh_user, ssh_key, package_path, gpg_public_key_file)

        # Extract and setup
        extract_and_setup(server_ip, ssh_port, ssh_user, ssh_key)

        # Run create.sh
        run_create_script(server_ip, ssh_port, ssh_user, ssh_key)

        # Get SSH private key
        ssh_private_key = get_ssh_private_key(server_ip, ssh_port, ssh_user, ssh_key)

        # Create installation flag
        create_installation_flag(server_ip, ssh_port, ssh_user, ssh_key)

        # Restart SSH service to apply hardening
        restart_ssh_service(server_ip, ssh_port, ssh_user, ssh_key)

        # Cleanup /tmp artifacts
        cleanup_server_temp_files(server_ip, ssh_port, ssh_user, ssh_key)

        # Save output
        output_file = save_output(gpg_private_key, ssh_private_key)

        logger.info("Installation completed successfully")
        logger.info(f"All credentials saved to: {output_file}")

    except KeyboardInterrupt:
        logger.info("Installation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.info(f"Installation failed: {e}")
        sys.exit(1)
    finally:
        # Cleanup temporary directories
        cleanup_temp_directories(temp_dirs)


if __name__ == "__main__":
    main()
