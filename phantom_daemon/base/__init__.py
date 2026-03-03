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

Base startup services: secrets, environment, wallet.
"""

from phantom_daemon.base.env import DaemonEnv, load_env
from phantom_daemon.base.errors import (
    SecretsError,
    StartupError,
    WalletError,
    WalletFullError,
)
from phantom_daemon.base.secrets import ServerKeys, load_secrets
from phantom_daemon.base.wallet import Wallet, open_wallet

__all__ = [
    "DaemonEnv",
    "SecretsError",
    "ServerKeys",
    "StartupError",
    "Wallet",
    "WalletError",
    "WalletFullError",
    "load_env",
    "load_secrets",
    "open_wallet",
]
