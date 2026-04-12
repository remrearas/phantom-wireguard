"""
Setup Module — Certificate Utilities

A minimal openssl wrapper that produces a single self-signed
certificate / private-key pair using the defaults loaded from the
packaged ``cert_defaults.json``:

    1. Read defaults from packaged JSON.
    2. Generate an EC private key.
    3. Generate an x509 self-signed cert from that key with the
       configured CN and validity.

Operators who want a CA-issued cert place their own ``tls_cert``
and ``tls_key`` files into ``secrets/`` and run ``ghost restart``.

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0
"""

import json
from pathlib import Path
from typing import Any, Callable, Dict, Optional


# Path to the packaged defaults file. Lives next to this lib so the
# install layout never has to think about it.
DEFAULTS_PATH = Path(__file__).parent.parent / "data" / "cert_defaults.json"


def load_cert_defaults() -> Dict[str, Any]:
    """Load TLS cert defaults from the packaged JSON file."""
    with open(DEFAULTS_PATH, "r") as f:
        return json.load(f)


def build_subject_string(
    common_name: str,
    organization: Optional[str] = None,
) -> str:
    """Build an OpenSSL subject string.

    Always starts with ``/CN=...``. Adds ``/O=...`` only if the
    defaults file specifies an organization.
    """
    parts = [f"/CN={common_name}"]
    if organization:
        parts.append(f"/O={organization}")
    return "".join(parts)


def generate_self_signed(
    cert_path: Path,
    key_path: Path,
    *,
    common_name: str,
    organization: Optional[str],
    validity_days: int,
    key_curve: str,
    run_command_func: Callable,
    logger,
) -> bool:
    """Produce an EC private key + a self-signed x509 certificate.

    Both files are written to the caller-supplied paths with
    restrictive permissions (key 0600, cert 0644). Returns True on
    success; logs and returns False on any failure.
    """
    cert_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. EC private key
    key_result = run_command_func([
        "openssl", "ecparam",
        "-name", key_curve,
        "-genkey",
        "-noout",
        "-out", str(key_path),
    ])
    if not key_result["success"]:
        logger.error(f"EC key generation failed: {key_result['stderr']}")
        return False

    try:
        key_path.chmod(0o600)
    except OSError as e:
        logger.warning(f"Could not chmod {key_path}: {e}")

    # 2. Self-signed cert from that key
    subject = build_subject_string(common_name, organization)
    cert_result = run_command_func([
        "openssl", "req",
        "-x509",
        "-new",
        "-key", str(key_path),
        "-out", str(cert_path),
        "-days", str(validity_days),
        "-subj", subject,
    ])
    if not cert_result["success"]:
        logger.error(f"Certificate generation failed: {cert_result['stderr']}")
        return False

    try:
        cert_path.chmod(0o644)
    except OSError as e:
        logger.warning(f"Could not chmod {cert_path}: {e}")

    logger.info(
        f"Self-signed cert generated: subject={subject!r}, "
        f"validity={validity_days}d, key={key_curve}"
    )
    return True