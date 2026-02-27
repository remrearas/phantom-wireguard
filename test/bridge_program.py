#!/usr/bin/env python3
"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""
"""
wireguard-go drop-in replacement using wireguard_go_bridge FFI.

Calls Run() which mirrors wireguard-go main.go foreground mode:
CreateTUN → NewDevice → UAPIOpen → UAPIListen → block until signal.

The wrapper script backgrounds this process with &.

Usage: python3 bridge_program.py <interface-name>
"""

import os
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(script_dir, ".."))

from wireguard_go_bridge import get_lib
from wireguard_go_bridge.types import check_error

if len(sys.argv) < 2:
    print(f"Usage: {sys.argv[0]} <interface-name>", file=sys.stderr)
    sys.exit(1)

check_error(get_lib().Run(sys.argv[1].encode("utf-8"), 2))