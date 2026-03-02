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

Preset schema validation for firewall_bridge v2.1.0

Pure Python, zero external dependencies.
Validates YAML preset structure before apply.
"""

from __future__ import annotations

import re

from .types import PresetValidationError


# ---- CIDR validation ----

_CIDR_V4 = re.compile(
    r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/(\d{1,2})$"
)
_CIDR_V6 = re.compile(r"^[0-9a-fA-F:]+/\d{1,3}$")


def _is_cidr(value: str) -> bool:
    """Check if value is valid CIDR notation (IPv4 or IPv6)."""
    m = _CIDR_V4.match(value)
    if m:
        octets = [int(m.group(i)) for i in range(1, 5)]
        prefix = int(m.group(5))
        return all(0 <= o <= 255 for o in octets) and 0 <= prefix <= 32
    return bool(_CIDR_V6.match(value))


# ---- Schema definitions ----

VALID_CHAINS = ("input", "output", "forward", "postrouting", "prerouting")
VALID_ACTIONS = ("accept", "drop", "reject", "masquerade")
VALID_FAMILIES = (2, 10)
VALID_PROTOS = ("", "tcp", "udp", "icmp")
VALID_TABLE_ENTRY_KEYS = ("ensure", "policy", "route")

ENSURE_FIELDS = {
    "id":   {"type": int, "required": True, "min": 1, "max": 65535},
    "name": {"type": str, "required": True},
}

POLICY_FIELDS = {
    "from":     {"type": str, "required": True, "format": "cidr"},
    "to":       {"type": str, "required": False, "format": "cidr"},
    "table":    {"type": str, "required": True},
    "priority": {"type": int, "required": True, "min": 0},
}

ROUTE_FIELDS = {
    "destination": {"type": str, "required": True},
    "device":      {"type": str, "required": True},
    "table":       {"type": str, "required": True},
}

RULE_FIELDS = {
    "chain":       {"type": str, "required": True, "enum": VALID_CHAINS},
    "action":      {"type": str, "required": True, "enum": VALID_ACTIONS},
    "family":      {"type": int, "required": False, "default": 2, "enum": VALID_FAMILIES},
    "proto":       {"type": str, "required": False, "default": "", "enum": VALID_PROTOS},
    "dport":       {"type": int, "required": False, "default": 0, "min": 0, "max": 65535},
    "source":      {"type": str, "required": False, "default": "", "format": "cidr_or_empty"},
    "destination": {"type": str, "required": False, "default": "", "format": "cidr_or_empty"},
    "in_iface":    {"type": str, "required": False, "default": ""},
    "out_iface":   {"type": str, "required": False, "default": ""},
    "state":       {"type": str, "required": False, "default": ""},
}

PRESET_FIELDS = {
    "name":     {"type": str, "required": True},
    "priority": {"type": int, "required": False, "default": 100, "min": 0, "max": 999},
    "type":     {"type": str, "required": False, "default": "custom"},
    "metadata": {"type": dict, "required": False, "default": {}},
    "table":    {"type": list, "required": False},
    "rules":    {"type": list, "required": False},
}


# ---- Validation helpers ----

def _fail(path: str, reason: str, value: object = None) -> None:
    raise PresetValidationError(path, reason, value)


def _check_type(path: str, value: object, expected: type) -> None:
    if not isinstance(value, expected):
        _fail(path, f"expected {expected.__name__}", value)


def _check_unknown_keys(path: str, data: dict, allowed: set) -> None:
    unknown = set(data.keys()) - allowed
    if unknown:
        _fail(path, f"unknown keys: {', '.join(sorted(unknown))}")


def _validate_fields(path: str, data: dict, schema: dict) -> dict:
    """Validate a dict against a field schema. Returns dict with defaults."""
    _check_type(path, data, dict)
    _check_unknown_keys(path, data, set(schema.keys()))

    result = {}
    for key, spec in schema.items():
        if key in data:
            val = data[key]
            _check_type(f"{path}.{key}", val, spec["type"])

            if "enum" in spec and val not in spec["enum"]:
                _fail(f"{path}.{key}",
                      f"must be one of {list(spec['enum'])}", val)

            if "min" in spec and val < spec["min"]:
                _fail(f"{path}.{key}",
                      f"minimum is {spec['min']}", val)

            if "max" in spec and val > spec["max"]:
                _fail(f"{path}.{key}",
                      f"maximum is {spec['max']}", val)

            if "format" in spec:
                _check_format(f"{path}.{key}", val, spec["format"])

            result[key] = val
        elif spec.get("required"):
            _fail(f"{path}.{key}", "required field missing")
        elif "default" in spec:
            result[key] = spec["default"]

    return result


def _check_format(path: str, value: str, fmt: str) -> None:
    if fmt == "cidr":
        if not _is_cidr(value):
            _fail(path, "invalid CIDR notation", value)
    elif fmt == "cidr_or_empty":
        if value and not _is_cidr(value):
            _fail(path, "must be empty or valid CIDR", value)


# ---- Table entry validation ----

def _validate_table_entry(path: str, entry: dict) -> dict:
    """Validate a single table entry (ensure | policy | route)."""
    _check_type(path, entry, dict)

    keys = set(entry.keys())
    valid_keys = keys & set(VALID_TABLE_ENTRY_KEYS)
    unknown = keys - set(VALID_TABLE_ENTRY_KEYS)

    if unknown:
        _fail(path, f"unknown keys: {', '.join(sorted(unknown))}")

    if len(valid_keys) == 0:
        _fail(path, f"must contain one of: {', '.join(VALID_TABLE_ENTRY_KEYS)}")

    if len(valid_keys) > 1:
        _fail(path, "must contain exactly one of: "
              f"{', '.join(VALID_TABLE_ENTRY_KEYS)}")

    entry_type = valid_keys.pop()
    inner = entry[entry_type]

    if entry_type == "ensure":
        validated = _validate_fields(f"{path}.ensure", inner, ENSURE_FIELDS)
    elif entry_type == "policy":
        validated = _validate_fields(f"{path}.policy", inner, POLICY_FIELDS)
    else:
        validated = _validate_fields(f"{path}.route", inner, ROUTE_FIELDS)

    return {entry_type: validated}


# ---- Main validator ----

def validate_preset(spec: object) -> dict:
    """Validate a preset spec dict. Returns validated dict with defaults.

    Raises PresetValidationError on invalid input with field path + reason.
    """
    _check_type("preset", spec, dict)
    _check_unknown_keys("preset", spec, set(PRESET_FIELDS.keys()))

    result = _validate_fields("preset", spec, PRESET_FIELDS)

    # validate table entries
    if "table" in result:
        validated_table = []
        for i, entry in enumerate(result["table"]):
            validated_table.append(
                _validate_table_entry(f"preset.table[{i}]", entry)
            )
        result["table"] = validated_table

    # validate firewall rules
    if "rules" in result:
        validated_rules = []
        for i, rule in enumerate(result["rules"]):
            validated_rules.append(
                _validate_fields(f"preset.rules[{i}]", rule, RULE_FIELDS)
            )
        result["rules"] = validated_rules

    return result
