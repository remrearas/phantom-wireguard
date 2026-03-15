"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

TR: Ghost Mode SSL/TLS Yardımcı Fonksiyonları
    =========================================
    
    Let's Encrypt ile SSL sertifikası yönetimi, port açma/kapama ve
    sertifika temizleme işlemlerini sağlar.

EN: Ghost Mode SSL/TLS Utility Functions
    ====================================
    
    Provides SSL certificate management with Let's Encrypt, port opening/closing
    and certificate cleanup operations.

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

import os
import shutil
from pathlib import Path
from typing import Callable, Dict, Any


def setup_ssl(domain: str, logger, run_command_func: Callable) -> bool:
    """Setup SSL certificate for domain using Let's Encrypt.

    Args:
        domain: Domain name for certificate
        logger: Logger instance for output
        run_command_func: Function to execute system commands

    Returns:
        True if certificate obtained successfully
    """
    logger.info(f"Setting up SSL certificate for {domain}")

    # Temporarily open port 80 for certbot validation
    open_ssl_ports(run_command_func)

    try:
        # Install certbot if not available
        # noinspection PyDeprecation
        if not shutil.which("certbot"):
            logger.info("Installing certbot...")
            run_command_func(["apt-get", "update", "-qq"])
            run_command_func(["apt-get", "install", "-y", "-qq", "certbot"])

        cert_cmd = [
            "certbot", "certonly", "--standalone",
            "-d", domain,
            "--non-interactive",
            "--agree-tos",
            "--register-unsafely-without-email",
            "--keep-until-expiring"
        ]

        if os.getenv("PHANTOM_TEST") == "1":
            # Test mode: use self-signed certificates
            run_command_func(["mkdir", "-p", f"/etc/letsencrypt/live/{domain}"])

            cert_cmd = [
                "openssl", "req", "-x509", "-newkey", "rsa:4096",
                "-keyout", f"/etc/letsencrypt/live/{domain}/privkey.pem",
                "-out", f"/etc/letsencrypt/live/{domain}/fullchain.pem",
                "-days", "365", "-nodes",
                "-subj", f"/CN={domain}"
            ]

        result = run_command_func(cert_cmd)

        if result["success"]:
            # Verify certificate files exist
            cert_path = Path(f"/etc/letsencrypt/live/{domain}/fullchain.pem")
            key_path = Path(f"/etc/letsencrypt/live/{domain}/privkey.pem")

            if cert_path.exists() and key_path.exists():
                logger.info("SSL certificate obtained successfully")
                return True

        logger.error("Failed to obtain SSL certificate")
        return False

    finally:
        # Ensure port 80 is closed after attempt
        close_ssl_ports(run_command_func)


def open_ssl_ports(run_command_func: Callable):
    """Open port 80 for SSL certificate validation.

    Args:
        run_command_func: Function to execute system commands
    """
    ufw_status = run_command_func(["ufw", "status"])

    if "Status: active" in ufw_status.get("stdout", ""):
        run_command_func(["ufw", "allow", "80/tcp"])


def close_ssl_ports(run_command_func: Callable):
    """Close port 80 after SSL certificate validation.

    Args:
        run_command_func: Function to execute system commands
    """
    ufw_status = run_command_func(["ufw", "status"])

    if "Status: active" in ufw_status.get("stdout", ""):
        run_command_func(["ufw", "delete", "allow", "80/tcp"])


def remove_certificates(state: Dict[str, Any], run_command_func: Callable, logger):
    """Remove SSL certificates and related files.

    Args:
        state: State dictionary containing domain
        run_command_func: Function to execute system commands
        logger: Logger instance for output
    """
    domain = state.get("domain")
    if not domain:
        return

    logger.info(f"Removing SSL certificates for {domain}")
    cert_dir = Path(f"/etc/letsencrypt/live/{domain}")
    if cert_dir.exists():
        run_command_func(["rm", "-rf", str(cert_dir)])

    # Archive directory contains all certificate versions
    archive_dir = Path(f"/etc/letsencrypt/archive/{domain}")
    if archive_dir.exists():
        run_command_func(["rm", "-rf", str(archive_dir)])

    renewal_conf = Path(f"/etc/letsencrypt/renewal/{domain}.conf")
    if renewal_conf.exists():
        run_command_func(["rm", "-f", str(renewal_conf)])
