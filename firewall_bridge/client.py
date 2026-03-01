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

FirewallClient — High-level Python interface to firewall-bridge v2.
Mirrors wireguard_go_bridge.BridgeClient pattern.
"""

import json
import logging
from typing import Optional

import firewall_bridge._ffi as _ffi_mod
from ._ffi import get_lib, _read_and_free, LOG_CALLBACK_TYPE
from .models import (
    FirewallRule, FirewallStatus, RuleGroup, RoutingRule, VerifyResult,
    _to_dataclass,
)
from .types import check_error

_log = logging.getLogger("firewall_bridge")

# Log level mapping: Rust → Python
_LEVEL_MAP = {
    0: logging.ERROR,    # LOG_ERROR
    1: logging.WARNING,  # LOG_WARN
    2: logging.INFO,     # LOG_INFO
    3: logging.DEBUG,    # LOG_DEBUG
}

_log_callback_registered = False


def _setup_log_callback():
    """Register native Rust→Python log callback (once)."""
    global _log_callback_registered
    if _log_callback_registered:
        return

    def _callback(level, message, _context):
        py_level = _LEVEL_MAP.get(level, logging.DEBUG)
        text = message.decode("utf-8") if message else ""
        _log.log(py_level, text)

    _ffi_mod._active_log_callback = LOG_CALLBACK_TYPE(_callback)
    get_lib().firewall_bridge_set_log_callback(_ffi_mod._active_log_callback, None)
    _log_callback_registered = True


def _encode(s: str) -> bytes:
    return s.encode("utf-8")


class FirewallClient:
    """Stateful firewall bridge client with SQLite-backed rule management."""

    def __init__(self, db_path: str):
        _setup_log_callback()
        self._lib = get_lib()
        check_error(self._lib.firewall_bridge_init(_encode(db_path)))

    def close(self) -> None:
        check_error(self._lib.firewall_bridge_close())

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ---- Lifecycle ----

    def start(self) -> None:
        check_error(self._lib.firewall_bridge_start())

    def stop(self) -> None:
        check_error(self._lib.firewall_bridge_stop())

    def get_status(self) -> FirewallStatus:
        raw = _read_and_free(self._lib.firewall_bridge_get_status())
        data = json.loads(raw) if raw else {}
        return _to_dataclass(FirewallStatus, data)

    # ---- Rule Groups ----

    def create_rule_group(self, name: str, group_type: str = "custom",
                          priority: int = 100) -> RuleGroup:
        raw = _read_and_free(self._lib.fw_create_rule_group(
            _encode(name), _encode(group_type), priority))
        return _to_dataclass(RuleGroup, json.loads(raw))

    def delete_rule_group(self, name: str) -> None:
        check_error(self._lib.fw_delete_rule_group(_encode(name)))

    def enable_rule_group(self, name: str) -> None:
        check_error(self._lib.fw_enable_rule_group(_encode(name)))

    def disable_rule_group(self, name: str) -> None:
        check_error(self._lib.fw_disable_rule_group(_encode(name)))

    def list_rule_groups(self) -> list[RuleGroup]:
        raw = _read_and_free(self._lib.fw_list_rule_groups())
        items = json.loads(raw) if raw else []
        return [_to_dataclass(RuleGroup, d) for d in items]

    def get_rule_group(self, name: str) -> RuleGroup:
        raw = _read_and_free(self._lib.fw_get_rule_group(_encode(name)))
        return _to_dataclass(RuleGroup, json.loads(raw))

    # ---- Firewall Rules ----

    def add_firewall_rule(self, group_name: str, chain: str, rule_type: str,
                          family: int = 2, proto: str = "", dport: int = 0,
                          source: str = "", destination: str = "",
                          in_iface: str = "", out_iface: str = "",
                          state_match: str = "") -> int:
        result = self._lib.fw_add_rule(
            _encode(group_name), _encode(chain), _encode(rule_type),
            family, _encode(proto), dport, _encode(source), _encode(destination),
            _encode(in_iface), _encode(out_iface), _encode(state_match),
        )
        if result < 0:
            check_error(int(result))
        return int(result)

    def remove_firewall_rule(self, rule_id: int) -> None:
        check_error(self._lib.fw_remove_rule(rule_id))

    def list_firewall_rules(self, group_name: Optional[str] = None) -> list[FirewallRule]:
        raw = _read_and_free(self._lib.fw_list_rules(
            _encode(group_name) if group_name else None))
        items = json.loads(raw) if raw else []
        return [_to_dataclass(FirewallRule, d) for d in items]

    # ---- Routing Rules ----

    def add_routing_rule(self, group_name: str, rule_type: str,
                         from_network: str = "", to_network: str = "",
                         table_name: str = "", table_id: int = 0,
                         priority: int = 0, destination: str = "",
                         device: str = "", fwmark: int = 0) -> int:
        result = self._lib.rt_add_rule(
            _encode(group_name), _encode(rule_type),
            _encode(from_network), _encode(to_network),
            _encode(table_name), table_id, priority,
            _encode(destination), _encode(device), fwmark,
        )
        if result < 0:
            check_error(int(result))
        return int(result)

    def remove_routing_rule(self, rule_id: int) -> None:
        check_error(self._lib.rt_remove_rule(rule_id))

    def list_routing_rules(self, group_name: Optional[str] = None) -> list[RoutingRule]:
        raw = _read_and_free(self._lib.rt_list_rules(
            _encode(group_name) if group_name else None))
        items = json.loads(raw) if raw else []
        return [_to_dataclass(RoutingRule, d) for d in items]

    # ---- Presets ----

    def apply_preset_vpn(self, name: str, wg_iface: str, wg_port: int,
                         wg_subnet: str, out_iface: str) -> RuleGroup:
        raw = _read_and_free(self._lib.fw_apply_preset_vpn(
            _encode(name), _encode(wg_iface), wg_port,
            _encode(wg_subnet), _encode(out_iface)))
        return _to_dataclass(RuleGroup, json.loads(raw))

    def apply_preset_multihop(self, name: str, in_iface: str, out_iface: str,
                              fwmark: int, table_id: int, subnet: str) -> RuleGroup:
        raw = _read_and_free(self._lib.fw_apply_preset_multihop(
            _encode(name), _encode(in_iface), _encode(out_iface),
            fwmark, table_id, _encode(subnet)))
        return _to_dataclass(RuleGroup, json.loads(raw))

    def apply_preset_kill_switch(self, wg_port: int, wstunnel_port: int = 0,
                                 wg_iface: str = "wg0") -> RuleGroup:
        raw = _read_and_free(self._lib.fw_apply_preset_kill_switch(
            wg_port, wstunnel_port, _encode(wg_iface)))
        return _to_dataclass(RuleGroup, json.loads(raw))

    def apply_preset_dns_protection(self, wg_iface: str = "wg0") -> RuleGroup:
        raw = _read_and_free(self._lib.fw_apply_preset_dns_protection(
            _encode(wg_iface)))
        return _to_dataclass(RuleGroup, json.loads(raw))

    def apply_preset_ipv6_block(self) -> RuleGroup:
        raw = _read_and_free(self._lib.fw_apply_preset_ipv6_block())
        return _to_dataclass(RuleGroup, json.loads(raw))

    def remove_preset(self, name: str) -> None:
        check_error(self._lib.fw_remove_preset(_encode(name)))

    # ---- Verify ----

    def get_kernel_state(self) -> dict:
        raw = _read_and_free(self._lib.fw_get_kernel_state())
        return json.loads(raw) if raw else {}

    def verify_rules(self) -> VerifyResult:
        raw = _read_and_free(self._lib.fw_verify_rules())
        data = json.loads(raw) if raw else {}
        return _to_dataclass(VerifyResult, data)

    # ---- Utilities ----

    def enable_ip_forward(self) -> None:
        check_error(self._lib.rt_enable_ip_forward())

    def flush_cache(self) -> None:
        check_error(self._lib.rt_flush_cache())

    def flush_table(self) -> None:
        check_error(self._lib.fw_flush_table())

    def get_version(self) -> str:
        result = self._lib.firewall_bridge_get_version()
        return result.decode("utf-8") if result else "unknown"
