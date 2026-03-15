"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Multihop Type-Safe Models

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from phantom.models.base import BaseModel


@dataclass
class VPNExitInfo(BaseModel):
    name: str
    endpoint: str
    active: bool
    provider: str
    imported_at: Optional[str] = None
    multihop_enhanced: bool = False

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "name": self.name,
            "endpoint": self.endpoint,
            "active": self.active,
            "provider": self.provider
        }
        if self.imported_at:
            result["imported_at"] = self.imported_at
        result["multihop_enhanced"] = self.multihop_enhanced
        return result


@dataclass
class MultihopState(BaseModel):
    enabled: bool
    active_exit: Optional[str]
    available_exits: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "active_exit": self.active_exit,
            "available_exits": self.available_exits
        }


@dataclass
class ImportResult(BaseModel):
    success: bool
    exit_name: str
    message: str
    optimizations: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "success": self.success,
            "exit_name": self.exit_name,
            "message": self.message
        }
        if self.optimizations:
            result["optimizations"] = self.optimizations  # type: ignore
        return result


@dataclass
class EnableMultihopResult(BaseModel):
    exit_name: str
    multihop_enabled: bool
    handshake_established: bool
    connection_verified: bool
    monitor_started: bool
    traffic_flow: str
    peer_access: str
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exit_name": self.exit_name,
            "multihop_enabled": self.multihop_enabled,
            "handshake_established": self.handshake_established,
            "connection_verified": self.connection_verified,
            "monitor_started": self.monitor_started,
            "traffic_flow": self.traffic_flow,
            "peer_access": self.peer_access,
            "message": self.message
        }


@dataclass
class DeactivationResult(BaseModel):
    multihop_enabled: bool
    previous_exit: Optional[str]
    interface_cleaned: bool
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "multihop_enabled": self.multihop_enabled,
            "previous_exit": self.previous_exit,
            "interface_cleaned": self.interface_cleaned,
            "message": self.message
        }


@dataclass
class RemoveConfigResult(BaseModel):
    removed: str
    was_active: bool
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "removed": self.removed,
            "was_active": self.was_active,
            "message": self.message
        }


@dataclass
class TestResult(BaseModel):
    passed: bool
    host: Optional[str] = None
    vpn_ip: Optional[str] = None
    has_recent_handshake: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {"passed": self.passed}
        if self.host is not None:
            result["host"] = self.host  # type: ignore
        if self.vpn_ip is not None:
            result["vpn_ip"] = self.vpn_ip  # type: ignore
        if self.has_recent_handshake is not None:
            result["has_recent_handshake"] = self.has_recent_handshake
        return result


@dataclass
class VPNTestResult(BaseModel):
    exit_name: str
    endpoint: str
    tests: Dict[str, TestResult]
    all_tests_passed: bool
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exit_name": self.exit_name,
            "endpoint": self.endpoint,
            "tests": {k: v.to_dict() for k, v in self.tests.items()},
            "all_tests_passed": self.all_tests_passed,
            "message": self.message
        }


@dataclass
class ResetStateResult(BaseModel):
    reset_complete: bool
    cleanup_successful: bool
    cleaned_up: List[str]
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reset_complete": self.reset_complete,
            "cleanup_successful": self.cleanup_successful,
            "cleaned_up": self.cleaned_up,
            "message": self.message
        }


@dataclass
class SessionLog(BaseModel):
    timestamp: str
    exit_name: str
    event: str
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "timestamp": self.timestamp,
            "exit_name": self.exit_name,
            "event": self.event
        }
        if self.details:
            result["details"] = self.details  # type: ignore
        return result


@dataclass
class ListExitsResult(BaseModel):
    exits: List[VPNExitInfo]
    multihop_enabled: bool
    active_exit: Optional[str]
    total: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exits": [_exit.to_dict() for _exit in self.exits],
            "multihop_enabled": self.multihop_enabled,
            "active_exit": self.active_exit,
            "total": self.total
        }


@dataclass
class MultihopStatusResult(BaseModel):
    enabled: bool
    active_exit: Optional[str]
    available_configs: int
    vpn_interface: Dict[str, Any]
    monitor_status: Dict[str, Any]
    traffic_routing: str
    traffic_flow: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "active_exit": self.active_exit,
            "available_configs": self.available_configs,
            "vpn_interface": self.vpn_interface,
            "monitor_status": self.monitor_status,
            "traffic_routing": self.traffic_routing,
            "traffic_flow": self.traffic_flow
        }
