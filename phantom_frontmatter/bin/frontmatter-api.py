#!/opt/phantom-frontmatter/.phantom-venv/bin/python3
"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Phantom-WG Frontmatter — API Command-Line Interface

Provides command-line access to the FrontmatterAPI. All responses
are returned as JSON.

Usage:
    frontmatter-api <module> <action> [key=value]...
    frontmatter-api --list-modules
    frontmatter-api --list-actions <module>
    frontmatter-api --help

Examples:
    frontmatter-api setup init backend=203.0.113.5
    frontmatter-api setup init backend=203.0.113.5:51820
    frontmatter-api setup status
    frontmatter-api setup clean yes=true
    frontmatter-api ghost start
    frontmatter-api ghost stop
    frontmatter-api ghost restart
    frontmatter-api ghost status
    frontmatter-api ghost client_config

Parameter formats:
    Simple:  key=value
    JSON:    key='[1,2,3]'  or  key='{"a":1}'
    Boolean: key=true | key=false
    Numbers: automatically parsed if digit-only

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

import json
import sys
from typing import Any, Dict, List

# Make package importable no matter how the script is invoked
from path_helper import setup_path
setup_path()

from phantom_frontmatter import __version__
from phantom_frontmatter.api import (
    FrontmatterAPI,
    FrontmatterException,
)


# ── Parameter parsing ─────────────────────────────────────────────

def parse_params(args: List[str]) -> Dict[str, Any]:
    """Parse key=value CLI arguments into a dict.

    Supports:
        - Simple strings:  key=value
        - JSON values:     key='[1,2]'  key='{"a":1}'
        - Booleans:        key=true | key=false
        - Null:            key=null
        - Integers:        key=42
        - Floats:          key=3.14
    """
    params: Dict[str, Any] = {}
    for arg in args:
        if "=" not in arg:
            raise ValueError(
                f"Invalid parameter {arg!r} — expected key=value"
            )
        key, _, value = arg.partition("=")
        params[key.strip()] = _parse_value(value)
    return params


def _parse_value(value: str) -> Any:
    """Coerce a string value to the most appropriate Python type."""
    lower = value.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    if lower == "null" or lower == "none":
        return None

    # Try JSON first (handles lists, dicts, numbers, quoted strings)
    stripped = value.strip()
    if stripped and stripped[0] in '[{"':
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass

    # Integer
    if value.lstrip("-").isdigit():
        try:
            return int(value)
        except ValueError:
            pass

    # Float
    try:
        return float(value)
    except ValueError:
        pass

    # Fallback: raw string
    return value


# ── Output helpers ────────────────────────────────────────────────

def _print_json(obj: Any) -> None:
    print(json.dumps(obj, indent=2, default=str))


def print_usage() -> None:
    """Print usage information to stdout."""
    print(__doc__.strip())


def print_version() -> None:
    print(f"frontmatter-api {__version__}")


# ── Commands ──────────────────────────────────────────────────────

def cmd_list_modules(api: FrontmatterAPI) -> int:
    modules = api.list_modules()
    result = {
        "modules": [
            {
                "name": name,
                "description": api.get_module(name).get_module_description(),
            }
            for name in modules
        ],
    }
    _print_json(result)
    return 0


def cmd_list_actions(api: FrontmatterAPI, module_name: str) -> int:
    try:
        actions = api.list_actions(module_name)
    except Exception as e:
        _print_json({"success": False, "error": str(e)})
        return 1
    _print_json({"module": module_name, "actions": actions})
    return 0


def cmd_execute(
    api: FrontmatterAPI,
    module: str,
    action: str,
    params: Dict[str, Any],
) -> int:
    response = api.execute(module, action, **params)
    print(response.to_json())
    return 0 if response.success else 1


# ── Main ──────────────────────────────────────────────────────────

def main() -> int:
    argv = sys.argv[1:]

    # Meta commands
    if not argv or argv[0] in ("-h", "--help", "help"):
        print_usage()
        return 0

    if argv[0] in ("-v", "--version"):
        print_version()
        return 0

    if argv[0] == "--list-modules":
        return cmd_list_modules(FrontmatterAPI())

    if argv[0] == "--list-actions":
        if len(argv) < 2:
            print("Error: --list-actions requires a module name", file=sys.stderr)
            return 2
        return cmd_list_actions(FrontmatterAPI(), argv[1])

    # module action [key=value]...
    if len(argv) < 2:
        print_usage()
        return 2

    module = argv[0]
    action = argv[1]

    try:
        params = parse_params(argv[2:])
    except ValueError as e:
        _print_json({
            "success": False,
            "error": str(e),
            "module": module,
            "action": action,
        })
        return 2

    try:
        api = FrontmatterAPI()
    except FrontmatterException as e:
        _print_json({
            "success": False,
            "error": f"API initialization failed: {e}",
        })
        return 1
    except Exception as e:
        _print_json({
            "success": False,
            "error": f"Unexpected error during API initialization: {e}",
        })
        return 1

    return cmd_execute(api, module, action, params)


if __name__ == "__main__":
    sys.exit(main())
