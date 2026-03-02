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

YAML preset engine for firewall_bridge v2.1.0

Presets are resolved YAML documents (no template variables).
Two sections: table: (routing operations) and rules: (nftables).
Template rendering is the daemon's responsibility.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Union

import yaml

from .models import Group

if TYPE_CHECKING:
    from .bridge import FirewallBridge


def _load_spec(preset: Union[str, Path, dict]) -> dict:
    """Load preset spec from dict, raw YAML string, or file path.

    - dict → use directly
    - Path → read file, parse YAML
    - str  → parse as raw YAML
    """
    if isinstance(preset, dict):
        return preset
    if isinstance(preset, Path):
        if not preset.exists():
            raise FileNotFoundError(f"Preset not found: {preset}")
        return yaml.safe_load(preset.read_text(encoding="utf-8"))
    return yaml.safe_load(preset)


def apply_preset(bridge: FirewallBridge, preset: Union[str, Path, dict],
                  **override) -> Group:
    """Apply a resolved YAML preset to the bridge.

    Creates a rule group and populates it with routing + firewall rules.
    If the bridge is started, rules are applied to kernel immediately.

    YAML format:
        name: preset-name
        priority: 80
        metadata: {description: "..."}
        table:
          - ensure: {id: 200, name: mh}
          - policy: {from: 10.0.1.0/24, table: mh, priority: 100}
          - route:  {destination: default, device: wg_exit, table: mh}
        rules:
          - chain: forward
            action: accept
            in_iface: wg_main
            out_iface: wg_exit
    """
    from .schema import validate_preset
    spec = validate_preset(_load_spec(preset))

    name = spec["name"]
    group_type = spec.get("type", "custom")
    priority = spec.get("priority", 100)

    metadata = dict(spec.get("metadata", {}))
    metadata.update(override)

    bridge.create_group(name, group_type, priority, metadata)

    # table: section — routing operations
    for entry in spec.get("table", []):
        if "ensure" in entry:
            e = entry["ensure"]
            bridge.add_routing_rule(
                group_name=name,
                rule_type="ensure",
                table_name=e.get("name", ""),
                table_id=e.get("id", 0),
            )
        elif "policy" in entry:
            p = entry["policy"]
            bridge.add_routing_rule(
                group_name=name,
                rule_type="policy",
                from_network=p.get("from", ""),
                to_network=p.get("to", ""),
                table_name=p.get("table", ""),
                priority=p.get("priority", 0),
            )
        elif "route" in entry:
            r = entry["route"]
            bridge.add_routing_rule(
                group_name=name,
                rule_type="route",
                destination=r.get("destination", ""),
                device=r.get("device", ""),
                table_name=r.get("table", ""),
            )

    # rules: section — nftables firewall rules
    for rule in spec.get("rules", []):
        bridge.add_firewall_rule(
            group_name=name,
            chain=rule.get("chain", ""),
            action=rule.get("action", ""),
            family=rule.get("family", 2),
            proto=rule.get("proto", ""),
            dport=rule.get("dport", 0),
            source=rule.get("source", ""),
            destination=rule.get("destination", ""),
            in_iface=rule.get("in_iface", ""),
            out_iface=rule.get("out_iface", ""),
            state_match=rule.get("state", ""),
        )

    return bridge.get_group(name)


def remove_preset(bridge: FirewallBridge, name: str) -> None:
    """Remove a preset rule group. Removes from kernel if started."""
    bridge.delete_group(name)


def enable_preset(bridge: FirewallBridge, name: str) -> None:
    """Enable a preset rule group. Applies to kernel if started."""
    bridge.enable_group(name)


def disable_preset(bridge: FirewallBridge, name: str) -> None:
    """Disable a preset rule group. Removes from kernel if started."""
    bridge.disable_group(name)


def list_presets(bridge: FirewallBridge) -> list[Group]:
    """List all rule groups."""
    return bridge.list_groups()


def get_preset(bridge: FirewallBridge, name: str) -> Group:
    """Get a preset rule group by name."""
    return bridge.get_group(name)
