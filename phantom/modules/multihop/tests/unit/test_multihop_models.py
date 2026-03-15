"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Multihop Models Unit Test

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

from phantom.modules.multihop.models.multihop_models import (
    VPNExitInfo,
    MultihopState,
    ImportResult,
    EnableMultihopResult,
    DeactivationResult,
    RemoveConfigResult,
    TestResult,
    VPNTestResult,
    ResetStateResult,
    SessionLog,
    ListExitsResult,
    MultihopStatusResult
)


class TestVPNExitInfo:

    def test_init_minimal(self):
        exit_info = VPNExitInfo(
            name="test-exit",
            endpoint="192.168.1.1:51820",
            active=False,
            provider="TestProvider"
        )
        assert exit_info.name == "test-exit"
        assert exit_info.endpoint == "192.168.1.1:51820"
        assert exit_info.active is False
        assert exit_info.provider == "TestProvider"
        assert exit_info.imported_at is None
        assert exit_info.multihop_enhanced is False

    def test_init_complete(self):
        exit_info = VPNExitInfo(
            name="test-exit",
            endpoint="192.168.1.1:51820",
            active=True,
            provider="TestProvider",
            imported_at="2025-01-01 10:00:00",
            multihop_enhanced=True
        )
        assert exit_info.imported_at == "2025-01-01 10:00:00"
        assert exit_info.multihop_enhanced is True

    def test_to_dict_minimal(self):
        exit_info = VPNExitInfo(
            name="test-exit",
            endpoint="192.168.1.1:51820",
            active=False,
            provider="TestProvider"
        )
        result = exit_info.to_dict()
        assert result == {
            "name": "test-exit",
            "endpoint": "192.168.1.1:51820",
            "active": False,
            "provider": "TestProvider",
            "multihop_enhanced": False
        }

    def test_to_dict_complete(self):
        exit_info = VPNExitInfo(
            name="test-exit",
            endpoint="192.168.1.1:51820",
            active=True,
            provider="TestProvider",
            imported_at="2025-01-01 10:00:00",
            multihop_enhanced=True
        )
        result = exit_info.to_dict()
        assert result == {
            "name": "test-exit",
            "endpoint": "192.168.1.1:51820",
            "active": True,
            "provider": "TestProvider",
            "imported_at": "2025-01-01 10:00:00",
            "multihop_enhanced": True
        }


class TestMultihopState:

    def test_init_and_to_dict(self):
        state = MultihopState(
            enabled=True,
            active_exit="test-exit",
            available_exits=["test-exit", "backup-exit"]
        )
        assert state.enabled is True
        assert state.active_exit == "test-exit"
        assert state.available_exits == ["test-exit", "backup-exit"]

        result = state.to_dict()
        assert result == {
            "enabled": True,
            "active_exit": "test-exit",
            "available_exits": ["test-exit", "backup-exit"]
        }

    def test_no_active_exit(self):
        state = MultihopState(
            enabled=False,
            active_exit=None,
            available_exits=["test-exit"]
        )
        assert state.active_exit is None
        assert state.to_dict()["active_exit"] is None


class TestImportResult:

    def test_init_minimal(self):
        result = ImportResult(
            success=True,
            exit_name="test-exit",
            message="Import successful"
        )
        assert result.success is True
        assert result.exit_name == "test-exit"
        assert result.message == "Import successful"
        assert result.optimizations is None

    def test_init_with_optimizations(self):
        result = ImportResult(
            success=True,
            exit_name="test-exit",
            message="Import successful",
            optimizations=["PersistentKeepalive set to 25", "MTU optimized"]
        )
        assert result.optimizations == ["PersistentKeepalive set to 25", "MTU optimized"]

    def test_to_dict_minimal(self):
        result = ImportResult(
            success=True,
            exit_name="test-exit",
            message="Import successful"
        )
        assert result.to_dict() == {
            "success": True,
            "exit_name": "test-exit",
            "message": "Import successful"
        }

    def test_to_dict_with_optimizations(self):
        result = ImportResult(
            success=True,
            exit_name="test-exit",
            message="Import successful",
            optimizations=["PersistentKeepalive set to 25"]
        )
        assert result.to_dict() == {
            "success": True,
            "exit_name": "test-exit",
            "message": "Import successful",
            "optimizations": ["PersistentKeepalive set to 25"]
        }


class TestEnableMultihopResult:

    def test_init_and_to_dict(self):
        result = EnableMultihopResult(
            exit_name="test-exit",
            multihop_enabled=True,
            handshake_established=True,
            connection_verified=True,
            monitor_started=True,
            traffic_flow="Clients → Phantom → VPN Exit (192.168.1.1:51820)",
            peer_access="Peers can still connect directly",
            message="Multihop enabled successfully"
        )

        assert result.exit_name == "test-exit"
        assert result.multihop_enabled is True
        assert result.handshake_established is True
        assert result.connection_verified is True
        assert result.monitor_started is True

        data = result.to_dict()
        assert data["exit_name"] == "test-exit"
        assert data["multihop_enabled"] is True
        assert data["handshake_established"] is True
        assert data["connection_verified"] is True
        assert data["monitor_started"] is True
        assert "192.168.1.1:51820" in data["traffic_flow"]
        assert data["peer_access"] == "Peers can still connect directly"
        assert data["message"] == "Multihop enabled successfully"


class TestDeactivationResult:

    def test_init_and_to_dict(self):
        result = DeactivationResult(
            multihop_enabled=False,
            previous_exit="test-exit",
            interface_cleaned=True,
            message="Multihop disabled successfully"
        )

        assert result.multihop_enabled is False
        assert result.previous_exit == "test-exit"
        assert result.interface_cleaned is True
        assert result.message == "Multihop disabled successfully"

        assert result.to_dict() == {
            "multihop_enabled": False,
            "previous_exit": "test-exit",
            "interface_cleaned": True,
            "message": "Multihop disabled successfully"
        }

    def test_no_previous_exit(self):
        result = DeactivationResult(
            multihop_enabled=False,
            previous_exit=None,
            interface_cleaned=True,
            message="No active multihop to disable"
        )
        assert result.previous_exit is None
        assert result.to_dict()["previous_exit"] is None


class TestRemoveConfigResult:

    def test_init_and_to_dict(self):
        result = RemoveConfigResult(
            removed="test-exit",
            was_active=True,
            message="Configuration removed successfully"
        )

        assert result.removed == "test-exit"
        assert result.was_active is True
        assert result.message == "Configuration removed successfully"

        assert result.to_dict() == {
            "removed": "test-exit",
            "was_active": True,
            "message": "Configuration removed successfully"
        }


class TestTestResult:

    def test_init_minimal(self):
        result = TestResult(passed=True)
        assert result.passed is True
        assert result.host is None
        assert result.vpn_ip is None
        assert result.has_recent_handshake is None

    def test_init_complete(self):
        result = TestResult(
            passed=True,
            host="vpn.example.com",
            vpn_ip="10.0.0.2",
            has_recent_handshake=True
        )
        assert result.host == "vpn.example.com"
        assert result.vpn_ip == "10.0.0.2"
        assert result.has_recent_handshake is True

    def test_to_dict_minimal(self):
        result = TestResult(passed=True)
        assert result.to_dict() == {"passed": True}

    def test_to_dict_complete(self):
        result = TestResult(
            passed=True,
            host="vpn.example.com",
            vpn_ip="10.0.0.2",
            has_recent_handshake=True
        )
        assert result.to_dict() == {
            "passed": True,
            "host": "vpn.example.com",
            "vpn_ip": "10.0.0.2",
            "has_recent_handshake": True
        }


class TestVPNTestResult:

    def test_init_and_to_dict(self):
        test1 = TestResult(passed=True, host="vpn.example.com")
        test2 = TestResult(passed=True, vpn_ip="10.0.0.2")

        result = VPNTestResult(
            exit_name="test-exit",
            endpoint="192.168.1.1:51820",
            tests={
                "dns_resolution": test1,
                "vpn_ip_check": test2
            },
            all_tests_passed=True,
            message="All tests passed"
        )

        assert result.exit_name == "test-exit"
        assert result.endpoint == "192.168.1.1:51820"
        assert result.all_tests_passed is True

        data = result.to_dict()
        assert data["exit_name"] == "test-exit"
        assert data["endpoint"] == "192.168.1.1:51820"
        assert data["all_tests_passed"] is True
        assert data["message"] == "All tests passed"
        assert "dns_resolution" in data["tests"]
        assert data["tests"]["dns_resolution"]["passed"] is True
        assert data["tests"]["dns_resolution"]["host"] == "vpn.example.com"


class TestResetStateResult:

    def test_init_and_to_dict(self):
        result = ResetStateResult(
            reset_complete=True,
            cleanup_successful=True,
            cleaned_up=["wg_vpn interface", "routing rules", "iptables rules"],
            message="State reset successfully"
        )

        assert result.reset_complete is True
        assert result.cleanup_successful is True
        assert len(result.cleaned_up) == 3
        assert "wg_vpn interface" in result.cleaned_up

        data = result.to_dict()
        assert data["reset_complete"] is True
        assert data["cleanup_successful"] is True
        assert data["cleaned_up"] == ["wg_vpn interface", "routing rules", "iptables rules"]
        assert data["message"] == "State reset successfully"


class TestSessionLog:

    def test_init_minimal(self):
        log = SessionLog(
            timestamp="2025-01-01 10:00:00",
            exit_name="test-exit",
            event="multihop_enabled"
        )
        assert log.timestamp == "2025-01-01 10:00:00"
        assert log.exit_name == "test-exit"
        assert log.event == "multihop_enabled"
        assert log.details is None

    def test_init_with_details(self):
        log = SessionLog(
            timestamp="2025-01-01 10:00:00",
            exit_name="test-exit",
            event="handshake_received",
            details={"peer": "192.168.1.1", "latency": "25ms"}
        )
        assert log.details == {"peer": "192.168.1.1", "latency": "25ms"}

    def test_to_dict_minimal(self):
        log = SessionLog(
            timestamp="2025-01-01 10:00:00",
            exit_name="test-exit",
            event="multihop_enabled"
        )
        assert log.to_dict() == {
            "timestamp": "2025-01-01 10:00:00",
            "exit_name": "test-exit",
            "event": "multihop_enabled"
        }

    def test_to_dict_with_details(self):
        log = SessionLog(
            timestamp="2025-01-01 10:00:00",
            exit_name="test-exit",
            event="handshake_received",
            details={"peer": "192.168.1.1"}
        )
        assert log.to_dict() == {
            "timestamp": "2025-01-01 10:00:00",
            "exit_name": "test-exit",
            "event": "handshake_received",
            "details": {"peer": "192.168.1.1"}
        }


class TestListExitsResult:

    def test_init_and_to_dict(self):
        exit1 = VPNExitInfo(
            name="test-exit",
            endpoint="192.168.1.1:51820",
            active=True,
            provider="TestProvider"
        )
        exit2 = VPNExitInfo(
            name="backup-exit",
            endpoint="192.168.1.2:51820",
            active=False,
            provider="BackupProvider"
        )

        result = ListExitsResult(
            exits=[exit1, exit2],
            multihop_enabled=True,
            active_exit="test-exit",
            total=2
        )

        assert len(result.exits) == 2
        assert result.multihop_enabled is True
        assert result.active_exit == "test-exit"
        assert result.total == 2

        data = result.to_dict()
        assert len(data["exits"]) == 2
        assert data["exits"][0]["name"] == "test-exit"
        assert data["exits"][0]["active"] is True
        assert data["exits"][1]["name"] == "backup-exit"
        assert data["exits"][1]["active"] is False
        assert data["multihop_enabled"] is True
        assert data["active_exit"] == "test-exit"
        assert data["total"] == 2


class TestMultihopStatusResult:

    def test_init_and_to_dict(self):
        result = MultihopStatusResult(
            enabled=True,
            active_exit="test-exit",
            available_configs=2,
            vpn_interface={
                "active": True,
                "output": "wg_vpn interface details"
            },
            monitor_status={
                "running": True,
                "pid": 1234
            },
            traffic_routing="VPN Exit",
            traffic_flow="Clients -> Phantom Server -> VPN Exit -> Internet"
        )

        assert result.enabled is True
        assert result.active_exit == "test-exit"
        assert result.available_configs == 2
        assert result.vpn_interface["active"] is True
        assert result.monitor_status["running"] is True
        assert result.traffic_routing == "VPN Exit"

        data = result.to_dict()
        assert data["enabled"] is True
        assert data["active_exit"] == "test-exit"
        assert data["available_configs"] == 2
        assert data["vpn_interface"]["active"] is True
        assert data["monitor_status"]["running"] is True
        assert data["traffic_routing"] == "VPN Exit"
        assert "Clients -> Phantom Server -> VPN Exit -> Internet" == data["traffic_flow"]

    def test_no_active_exit(self):
        result = MultihopStatusResult(
            enabled=False,
            active_exit=None,
            available_configs=1,
            vpn_interface={"active": False},
            monitor_status={"running": False},
            traffic_routing="Direct",
            traffic_flow="Clients -> Phantom Server -> Internet"
        )
        assert result.active_exit is None
        assert result.to_dict()["active_exit"] is None
