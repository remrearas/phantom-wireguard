#!/opt/phantom-wg/.phantom-venv/bin/python3
"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Casper App - Ghost Mode .conf Configuration Exporter

    Generates WireGuard .conf format with optional [Wstunnel] section
    for Phantom-WG mobile and desktop applications.

    Usage:
        phantom-casper-app [username]
        phantom-casper-app --help

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from path_helper import setup_phantom_path

setup_phantom_path()

from tools.casper_app.core import CasperAppService


def show_help():
    print("Casper App - Ghost Mode .conf Configuration Exporter")
    print("=" * 54)
    print()
    print("Usage: phantom-casper-app [username]")
    print()
    print("Examples:")
    print("  phantom-casper-app john-laptop    # .conf output (Ghost)")
    print("  phantom-casper-app alice-phone    # .conf output (Ghost)")
    print()
    print("Requirements:")
    print("  - Ghost Mode must be active")
    print("  - Client must exist in the system")
    print()
    print("Output:")
    print("  - WireGuard .conf with [Wstunnel] section")
    print("  - No files created - stdout only")


def main():
    parser = argparse.ArgumentParser(
        description="Ghost Mode .conf Configuration Exporter",
        add_help=False,
    )
    parser.add_argument("username", nargs="?")
    parser.add_argument("--help", "-h", action="store_true")

    args = parser.parse_args()

    if args.help or not args.username:
        show_help()
        sys.exit(0)

    try:
        service = CasperAppService()
        service.export_client_config(args.username)
    except KeyboardInterrupt:
        print("\nOperation cancelled")
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
