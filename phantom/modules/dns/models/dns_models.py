"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

DNS Type-Safe Models

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.

"""
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

from phantom.models.base import BaseModel


@dataclass
class DNSServerConfig(BaseModel):
    primary: str
    secondary: str
    previous_primary: Optional[str] = None
    previous_secondary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "primary": self.primary,
            "secondary": self.secondary
        }
        if self.previous_primary is not None:
            result["previous_primary"] = self.previous_primary
        if self.previous_secondary is not None:
            result["previous_secondary"] = self.previous_secondary
        return result


@dataclass
class ClientConfigUpdateResult(BaseModel):
    success: bool
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message
        }


@dataclass
class ChangeDNSResult(BaseModel):
    success: bool
    dns_servers: DNSServerConfig
    client_configs_updated: ClientConfigUpdateResult

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "dns_servers": self.dns_servers.to_dict(),
            "client_configs_updated": self.client_configs_updated.to_dict()
        }


@dataclass
class DNSTestServerResult(BaseModel):
    server: str
    success: bool
    status: str
    response_time_ms: Optional[float] = None
    test_domain: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "server": self.server,
            "success": self.success,
            "status": self.status
        }
        if self.response_time_ms is not None:
            result["response_time_ms"] = self.response_time_ms  # type: ignore
        if self.test_domain is not None:
            result["test_domain"] = self.test_domain
        if self.error is not None:
            result["error"] = self.error
        return result


@dataclass
class TestDNSResult(BaseModel):
    all_passed: bool
    servers_tested: int
    results: List[DNSTestServerResult]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "all_passed": self.all_passed,
            "servers_tested": self.servers_tested,
            "results": [result.to_dict() for result in self.results]
        }


@dataclass
class DNSConfiguration(BaseModel):
    primary: str
    secondary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary": self.primary,
            "secondary": self.secondary
        }


@dataclass
class DNSDomainTest(BaseModel):
    domain: str
    success: Any  # Can be bool or string response
    response: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "domain": self.domain,
            "success": self.success
        }
        if self.response is not None:
            result["response"] = self.response
        if self.error is not None:
            result["error"] = self.error
        return result


@dataclass
class DNSServerStatusTest(BaseModel):
    server: str
    tests: List[DNSDomainTest]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "server": self.server,
            "tests": [test.to_dict() for test in self.tests]
        }


@dataclass
class DNSHealth(BaseModel):
    status: str
    test_results: List[DNSServerStatusTest]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "test_results": [result.to_dict() for result in self.test_results]
        }


@dataclass
class DNSStatusResult(BaseModel):
    configuration: DNSConfiguration
    health: DNSHealth

    def to_dict(self) -> Dict[str, Any]:
        return {
            "configuration": self.configuration.to_dict(),
            "health": self.health.to_dict()
        }


@dataclass
class GetDNSServersResult(BaseModel):
    primary: str
    secondary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary": self.primary,
            "secondary": self.secondary
        }
