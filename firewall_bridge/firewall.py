"""
FirewallManager — High-level Python wrapper for nftables firewall operations.

All rules live in the 'inet phantom' nftables table, isolated from
UFW, iptables, and any other rulesets.

Usage:
    fw = FirewallManager()
    fw.init()
    fw.add_input_accept("tcp", 443)
    fw.add_input_accept("udp", 51820, source="127.0.0.1")
    fw.add_input_drop("udp", 51820)
    fw.add_nat_masquerade("10.66.66.0/24", "eth0")
    fw.flush()
    fw.cleanup()

Or as context manager:
    with FirewallManager() as fw:
        fw.add_input_accept("tcp", 443)
"""

from typing import Optional

from ._ffi import get_lib
from .types import AddressFamily, check_error


class FirewallManager:
    """Manages nftables firewall rules via native bridge."""

    def __init__(self):
        self._lib = get_lib()
        self._initialized = False

    def init(self) -> None:
        """Initialize nftables context and ensure phantom table exists."""
        check_error(self._lib.firewall_bridge_init())
        self._initialized = True

    def cleanup(self) -> None:
        """Release nftables context."""
        if self._initialized:
            self._lib.firewall_bridge_cleanup()
            self._initialized = False

    # --- INPUT rules ---

    def add_input_accept(self, proto: str, dport: int,
                         source: Optional[str] = None,
                         family: AddressFamily = AddressFamily.INET) -> None:
        check_error(self._lib.fw_add_input_accept(
            int(family),
            proto.encode("utf-8"),
            dport,
            source.encode("utf-8") if source else None,
        ))

    def add_input_drop(self, proto: str, dport: int,
                       source: Optional[str] = None,
                       family: AddressFamily = AddressFamily.INET) -> None:
        check_error(self._lib.fw_add_input_drop(
            int(family),
            proto.encode("utf-8"),
            dport,
            source.encode("utf-8") if source else None,
        ))

    def del_input(self, proto: str, dport: int,
                  action: str = "accept",
                  source: Optional[str] = None,
                  family: AddressFamily = AddressFamily.INET) -> None:
        check_error(self._lib.fw_del_input(
            int(family),
            proto.encode("utf-8"),
            dport,
            source.encode("utf-8") if source else None,
            action.encode("utf-8"),
        ))

    # --- FORWARD rules ---

    def add_forward(self, in_iface: str, out_iface: str,
                    state_match: Optional[str] = None) -> None:
        check_error(self._lib.fw_add_forward(
            in_iface.encode("utf-8"),
            out_iface.encode("utf-8"),
            state_match.encode("utf-8") if state_match else None,
        ))

    def del_forward(self, in_iface: str, out_iface: str,
                    state_match: Optional[str] = None) -> None:
        check_error(self._lib.fw_del_forward(
            in_iface.encode("utf-8"),
            out_iface.encode("utf-8"),
            state_match.encode("utf-8") if state_match else None,
        ))

    # --- NAT rules ---

    def add_nat_masquerade(self, source_network: str,
                           out_iface: Optional[str] = None) -> None:
        check_error(self._lib.fw_add_nat_masquerade(
            source_network.encode("utf-8"),
            out_iface.encode("utf-8") if out_iface else None,
        ))

    def del_nat_masquerade(self, source_network: str,
                           out_iface: Optional[str] = None) -> None:
        check_error(self._lib.fw_del_nat_masquerade(
            source_network.encode("utf-8"),
            out_iface.encode("utf-8") if out_iface else None,
        ))

    # --- Query & Control ---

    def list_rules(self) -> str:
        """Return all phantom table rules as JSON string."""
        result = self._lib.fw_list_rules()
        if result:
            return result.decode("utf-8")
        return "{}"

    def flush(self) -> None:
        """Flush all rules in the phantom table."""
        check_error(self._lib.fw_flush_table())

    # --- Lifecycle ---

    def __enter__(self) -> "FirewallManager":
        self.init()
        return self

    def __exit__(self, *exc) -> None:
        self.cleanup()

    def __del__(self) -> None:
        self.cleanup()

    def __repr__(self) -> str:
        state = "initialized" if self._initialized else "idle"
        return f"FirewallManager({state})"