"""
Phantom-WG Frontmatter — Input Validators

Two validators: ``validate_ip`` and ``validate_port``. Both are
used by the setup module's ``_parse_backend`` helper.

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0
"""

import ipaddress

from .exceptions import ValidationError


def validate_ip(ip: str, *, allow_ipv6: bool = True) -> str:
    """Validate an IP address (v4 or v6). Returns the normalized form.

    Raises:
        ValidationError: If the input is not a valid IP address, or
            if it's IPv6 and ``allow_ipv6`` is False.
    """
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        raise ValidationError(f"Invalid IP address: {ip!r}")
    if isinstance(addr, ipaddress.IPv6Address) and not allow_ipv6:
        raise ValidationError(f"IPv6 not allowed here: {ip!r}")
    return str(addr)


def validate_port(port: int) -> int:
    """Validate a TCP/UDP port number (1-65535)."""
    try:
        port_int = int(port)
    except (TypeError, ValueError):
        raise ValidationError(f"Port must be an integer: {port!r}")
    if not 1 <= port_int <= 65535:
        raise ValidationError(f"Port out of range (1-65535): {port_int}")
    return port_int
