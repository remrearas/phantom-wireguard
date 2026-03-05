"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.

Startup error hierarchy for daemon initialisation phases.
"""

from __future__ import annotations


class StartupError(Exception):
    """Base error for daemon startup failures."""


class SecretsError(StartupError):
    """Failed to load or validate server key material."""


class WalletError(StartupError):
    """Failed to open or create wallet database."""


class WalletFullError(WalletError):
    """IP pool is exhausted, no free slots available."""


class WireGuardError(StartupError):
    """Failed to initialise or sync WireGuard bridge."""


class ExitStoreError(StartupError):
    """Failed to open, create, or query exit store database."""


class FirewallError(StartupError):
    """Failed to initialise or configure firewall bridge."""


class WstunnelError(StartupError):
    """Failed to initialise or operate wstunnel bridge."""
