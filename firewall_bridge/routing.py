"""
RoutingManager — High-level Python wrapper for routing operations.

Manages policy rules (ip rule) and routes (ip route) via netlink.
No subprocess calls — direct kernel communication.

Usage:
    rt = RoutingManager()
    rt.ensure_table(100, "multihop")
    rt.add_policy("10.66.66.0/24", "10.66.66.0/24", "main", priority=100)
    rt.add_policy("10.66.66.0/24", "", "multihop", priority=200)
    rt.add_route("default", "tun0", "multihop")
    rt.enable_ip_forward()
"""

from ._ffi import get_lib
from .types import check_error


class RoutingManager:
    """Manages routing policy rules and routes via native bridge."""

    def __init__(self):
        self._lib = get_lib()

    # --- Policy rules ---

    def add_policy(self, from_network: str, to_network: str,
                   table: str, priority: int) -> None:
        check_error(self._lib.rt_add_policy(
            from_network.encode("utf-8"),
            to_network.encode("utf-8") if to_network else None,
            table.encode("utf-8"),
            priority,
        ))

    def del_policy(self, from_network: str, to_network: str,
                   table: str, priority: int) -> None:
        check_error(self._lib.rt_del_policy(
            from_network.encode("utf-8"),
            to_network.encode("utf-8") if to_network else None,
            table.encode("utf-8"),
            priority,
        ))

    # --- Routes ---

    def add_route(self, destination: str, device: str, table: str) -> None:
        check_error(self._lib.rt_add_route(
            destination.encode("utf-8"),
            device.encode("utf-8"),
            table.encode("utf-8"),
        ))

    def del_route(self, destination: str, device: str, table: str) -> None:
        check_error(self._lib.rt_del_route(
            destination.encode("utf-8"),
            device.encode("utf-8"),
            table.encode("utf-8"),
        ))

    # --- Table management ---

    def ensure_table(self, table_id: int, table_name: str) -> None:
        check_error(self._lib.rt_ensure_table(
            table_id,
            table_name.encode("utf-8"),
        ))

    # --- Utilities ---

    def flush_cache(self) -> None:
        check_error(self._lib.rt_flush_cache())

    def enable_ip_forward(self) -> None:
        check_error(self._lib.rt_enable_ip_forward())

    def __repr__(self) -> str:
        return "RoutingManager()"