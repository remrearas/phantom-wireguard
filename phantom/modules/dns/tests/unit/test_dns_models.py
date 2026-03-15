"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

DNS Models Unit Test

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

from phantom.modules.dns.models.dns_models import (
    DNSServerConfig,
    ClientConfigUpdateResult,
    ChangeDNSResult,
    DNSTestServerResult,
    TestDNSResult,
    DNSConfiguration,
    DNSDomainTest,
    DNSServerStatusTest,
    DNSHealth,
    DNSStatusResult,
    GetDNSServersResult
)


class TestDNSServerConfig:

    def test_init_minimal(self):
        config = DNSServerConfig(primary="8.8.8.8", secondary="8.8.4.4")
        assert config.primary == "8.8.8.8"
        assert config.secondary == "8.8.4.4"
        assert config.previous_primary is None
        assert config.previous_secondary is None

    def test_init_with_previous(self):
        config = DNSServerConfig(
            primary="1.1.1.1",
            secondary="1.0.0.1",
            previous_primary="8.8.8.8",
            previous_secondary="8.8.4.4"
        )
        assert config.primary == "1.1.1.1"
        assert config.secondary == "1.0.0.1"
        assert config.previous_primary == "8.8.8.8"
        assert config.previous_secondary == "8.8.4.4"

    def test_to_dict_minimal(self):
        config = DNSServerConfig(primary="8.8.8.8", secondary="8.8.4.4")
        result = config.to_dict()
        assert result == {
            "primary": "8.8.8.8",
            "secondary": "8.8.4.4"
        }

    def test_to_dict_with_previous(self):
        config = DNSServerConfig(
            primary="1.1.1.1",
            secondary="1.0.0.1",
            previous_primary="8.8.8.8",
            previous_secondary="8.8.4.4"
        )
        result = config.to_dict()
        assert result == {
            "primary": "1.1.1.1",
            "secondary": "1.0.0.1",
            "previous_primary": "8.8.8.8",
            "previous_secondary": "8.8.4.4"
        }

    def test_to_dict_partial_previous(self):
        config = DNSServerConfig(
            primary="1.1.1.1",
            secondary="1.0.0.1",
            previous_primary="8.8.8.8"
        )
        result = config.to_dict()
        assert result == {
            "primary": "1.1.1.1",
            "secondary": "1.0.0.1",
            "previous_primary": "8.8.8.8"
        }


class TestClientConfigUpdateResult:

    def test_init_success(self):
        result = ClientConfigUpdateResult(success=True, message="Updated successfully")
        assert result.success is True
        assert result.message == "Updated successfully"

    def test_init_failure(self):
        result = ClientConfigUpdateResult(success=False, message="Update failed")
        assert result.success is False
        assert result.message == "Update failed"

    def test_to_dict(self):
        result = ClientConfigUpdateResult(success=True, message="Config updated")
        assert result.to_dict() == {
            "success": True,
            "message": "Config updated"
        }


class TestChangeDNSResult:

    def test_init_and_to_dict(self):
        dns_config = DNSServerConfig(primary="1.1.1.1", secondary="1.0.0.1")
        client_update = ClientConfigUpdateResult(success=True, message="Updated")

        result = ChangeDNSResult(
            success=True,
            dns_servers=dns_config,
            client_configs_updated=client_update
        )

        assert result.success is True
        assert result.dns_servers == dns_config
        assert result.client_configs_updated == client_update

        dict_result = result.to_dict()
        assert dict_result == {
            "success": True,
            "dns_servers": {
                "primary": "1.1.1.1",
                "secondary": "1.0.0.1"
            },
            "client_configs_updated": {
                "success": True,
                "message": "Updated"
            }
        }


class TestDNSTestServerResult:

    def test_init_minimal(self):
        result = DNSTestServerResult(
            server="8.8.8.8",
            success=True,
            status="OK"
        )
        assert result.server == "8.8.8.8"
        assert result.success is True
        assert result.status == "OK"
        assert result.response_time_ms is None
        assert result.test_domain is None
        assert result.error is None

    def test_init_complete(self):
        result = DNSTestServerResult(
            server="8.8.8.8",
            success=True,
            status="OK",
            response_time_ms=23.5,
            test_domain="example.com",
            error=None
        )
        assert result.server == "8.8.8.8"
        assert result.success is True
        assert result.status == "OK"
        assert result.response_time_ms == 23.5
        assert result.test_domain == "example.com"
        assert result.error is None

    def test_init_with_error(self):
        result = DNSTestServerResult(
            server="8.8.8.8",
            success=False,
            status="FAILED",
            error="Connection timeout"
        )
        assert result.server == "8.8.8.8"
        assert result.success is False
        assert result.status == "FAILED"
        assert result.error == "Connection timeout"

    def test_to_dict_minimal(self):
        result = DNSTestServerResult(
            server="8.8.8.8",
            success=True,
            status="OK"
        )
        assert result.to_dict() == {
            "server": "8.8.8.8",
            "success": True,
            "status": "OK"
        }

    def test_to_dict_complete(self):
        result = DNSTestServerResult(
            server="8.8.8.8",
            success=True,
            status="OK",
            response_time_ms=23.5,
            test_domain="example.com"
        )
        assert result.to_dict() == {
            "server": "8.8.8.8",
            "success": True,
            "status": "OK",
            "response_time_ms": 23.5,
            "test_domain": "example.com"
        }

    def test_to_dict_with_error(self):
        result = DNSTestServerResult(
            server="8.8.8.8",
            success=False,
            status="FAILED",
            error="Connection timeout"
        )
        assert result.to_dict() == {
            "server": "8.8.8.8",
            "success": False,
            "status": "FAILED",
            "error": "Connection timeout"
        }


class TestTestDNSResult:

    def test_init_empty_results(self):
        result = TestDNSResult(
            all_passed=True,
            servers_tested=0,
            results=[]
        )
        assert result.all_passed is True
        assert result.servers_tested == 0
        assert result.results == []

    def test_init_with_results(self):
        test_results = [
            DNSTestServerResult(server="8.8.8.8", success=True, status="OK"),
            DNSTestServerResult(server="1.1.1.1", success=True, status="OK")
        ]
        result = TestDNSResult(
            all_passed=True,
            servers_tested=2,
            results=test_results
        )
        assert result.all_passed is True
        assert result.servers_tested == 2
        assert len(result.results) == 2

    def test_to_dict(self):
        test_results = [
            DNSTestServerResult(server="8.8.8.8", success=True, status="OK"),
            DNSTestServerResult(server="1.1.1.1", success=False, status="FAILED", error="Timeout")
        ]
        result = TestDNSResult(
            all_passed=False,
            servers_tested=2,
            results=test_results
        )
        dict_result = result.to_dict()
        assert dict_result == {
            "all_passed": False,
            "servers_tested": 2,
            "results": [
                {"server": "8.8.8.8", "success": True, "status": "OK"},
                {"server": "1.1.1.1", "success": False, "status": "FAILED", "error": "Timeout"}
            ]
        }


class TestDNSConfiguration:

    def test_init(self):
        config = DNSConfiguration(primary="8.8.8.8", secondary="8.8.4.4")
        assert config.primary == "8.8.8.8"
        assert config.secondary == "8.8.4.4"

    def test_to_dict(self):
        config = DNSConfiguration(primary="1.1.1.1", secondary="1.0.0.1")
        assert config.to_dict() == {
            "primary": "1.1.1.1",
            "secondary": "1.0.0.1"
        }


class TestDNSDomainTest:

    def test_init_minimal(self):
        test = DNSDomainTest(domain="example.com", success=True)
        assert test.domain == "example.com"
        assert test.success is True
        assert test.response is None
        assert test.error is None

    def test_init_with_response(self):
        test = DNSDomainTest(
            domain="example.com",
            success=True,
            response="93.184.216.34"
        )
        assert test.domain == "example.com"
        assert test.success is True
        assert test.response == "93.184.216.34"
        assert test.error is None

    def test_init_with_error(self):
        test = DNSDomainTest(
            domain="example.com",
            success=False,
            error="NXDOMAIN"
        )
        assert test.domain == "example.com"
        assert test.success is False
        assert test.response is None
        assert test.error == "NXDOMAIN"

    def test_init_with_string_success(self):
        test = DNSDomainTest(
            domain="example.com",
            success="OK",
            response="93.184.216.34"
        )
        assert test.domain == "example.com"
        assert test.success == "OK"
        assert test.response == "93.184.216.34"

    def test_to_dict_minimal(self):
        test = DNSDomainTest(domain="example.com", success=True)
        assert test.to_dict() == {
            "domain": "example.com",
            "success": True
        }

    def test_to_dict_complete(self):
        test = DNSDomainTest(
            domain="example.com",
            success=True,
            response="93.184.216.34"
        )
        assert test.to_dict() == {
            "domain": "example.com",
            "success": True,
            "response": "93.184.216.34"
        }


class TestDNSServerStatusTest:

    def test_init_empty_tests(self):
        status = DNSServerStatusTest(server="8.8.8.8", tests=[])
        assert status.server == "8.8.8.8"
        assert status.tests == []

    def test_init_with_tests(self):
        domain_tests = [
            DNSDomainTest(domain="example.com", success=True),
            DNSDomainTest(domain="google.com", success=True)
        ]
        status = DNSServerStatusTest(server="8.8.8.8", tests=domain_tests)
        assert status.server == "8.8.8.8"
        assert len(status.tests) == 2

    def test_to_dict(self):
        domain_tests = [
            DNSDomainTest(domain="example.com", success=True, response="93.184.216.34"),
            DNSDomainTest(domain="invalid.test", success=False, error="NXDOMAIN")
        ]
        status = DNSServerStatusTest(server="8.8.8.8", tests=domain_tests)
        assert status.to_dict() == {
            "server": "8.8.8.8",
            "tests": [
                {"domain": "example.com", "success": True, "response": "93.184.216.34"},
                {"domain": "invalid.test", "success": False, "error": "NXDOMAIN"}
            ]
        }


class TestDNSHealth:

    def test_init(self):
        test_results = [
            DNSServerStatusTest(server="8.8.8.8", tests=[]),
            DNSServerStatusTest(server="1.1.1.1", tests=[])
        ]
        health = DNSHealth(status="healthy", test_results=test_results)
        assert health.status == "healthy"
        assert len(health.test_results) == 2

    def test_to_dict(self):
        domain_test = DNSDomainTest(domain="example.com", success=True)
        test_results = [
            DNSServerStatusTest(server="8.8.8.8", tests=[domain_test])
        ]
        health = DNSHealth(status="healthy", test_results=test_results)
        assert health.to_dict() == {
            "status": "healthy",
            "test_results": [
                {
                    "server": "8.8.8.8",
                    "tests": [
                        {"domain": "example.com", "success": True}
                    ]
                }
            ]
        }


class TestDNSStatusResult:

    def test_init_and_to_dict(self):
        config = DNSConfiguration(primary="8.8.8.8", secondary="8.8.4.4")
        health = DNSHealth(status="healthy", test_results=[])

        status = DNSStatusResult(
            configuration=config,
            health=health
        )

        assert status.configuration == config
        assert status.health == health

        assert status.to_dict() == {
            "configuration": {
                "primary": "8.8.8.8",
                "secondary": "8.8.4.4"
            },
            "health": {
                "status": "healthy",
                "test_results": []
            }
        }


class TestGetDNSServersResult:

    def test_init(self):
        result = GetDNSServersResult(primary="8.8.8.8", secondary="8.8.4.4")
        assert result.primary == "8.8.8.8"
        assert result.secondary == "8.8.4.4"

    def test_to_dict(self):
        result = GetDNSServersResult(primary="1.1.1.1", secondary="1.0.0.1")
        assert result.to_dict() == {
            "primary": "1.1.1.1",
            "secondary": "1.0.0.1"
        }

    def test_different_dns_servers(self):
        # Google DNS
        google = GetDNSServersResult(primary="8.8.8.8", secondary="8.8.4.4")
        assert google.to_dict() == {"primary": "8.8.8.8", "secondary": "8.8.4.4"}

        # Cloudflare DNS
        cloudflare = GetDNSServersResult(primary="1.1.1.1", secondary="1.0.0.1")
        assert cloudflare.to_dict() == {"primary": "1.1.1.1", "secondary": "1.0.0.1"}

        # OpenDNS
        opendns = GetDNSServersResult(primary="208.67.222.222", secondary="208.67.220.220")
        assert opendns.to_dict() == {"primary": "208.67.222.222", "secondary": "208.67.220.220"}
