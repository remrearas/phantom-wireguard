"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details

Integration: DB state persistence, crash recovery, self-signed TLS verify.

Ports: server=8448/8449
"""

import os
import subprocess
import tempfile
import time

import pytest

from wstunnel_bridge import WstunnelState, WstunnelDB, LogLevel
from .conftest import wait_for_port


@pytest.mark.docker
class TestStatePersistence:
    """DB state survives across WstunnelState instances."""

    def test_config_persists(self, uid):
        db_path = os.path.join(tempfile.gettempdir(), f"ws_persist_{uid}.db")

        # First instance: write config
        s1 = WstunnelState()
        s1.init(db_path)
        s1.db().set_client_config(
            remote_url="wss://persist.test:443",
            http_upgrade_path_prefix="ghost-secret",
            tls_verify=0,
        )
        s1.db().add_tunnel("udp", "127.0.0.1", 51820, "127.0.0.1", 51820)
        s1.db().add_tunnel("tcp", "127.0.0.1", 8080, "10.0.0.1", 80)
        s1.db().add_http_header("X-Ghost", "true")
        s1.close()

        # Second instance: verify
        s2 = WstunnelState()
        s2.init(db_path)
        cfg = s2.db().get_client_config()
        tunnels = s2.db().list_tunnels()
        headers = s2.db().list_http_headers()

        assert cfg["remote_url"] == "wss://persist.test:443"
        assert cfg["http_upgrade_path_prefix"] == "ghost-secret"
        assert len(tunnels) == 2
        assert tunnels[0]["tunnel_type"] == "udp"
        assert tunnels[1]["tunnel_type"] == "tcp"
        assert len(headers) == 1
        assert headers[0]["name"] == "X-Ghost"

        s2.close()
        for ext in ("", "-wal", "-shm"):
            p = db_path + ext
            if os.path.exists(p):
                os.remove(p)

    def test_server_config_persists(self, uid, certs):
        db_path = os.path.join(tempfile.gettempdir(), f"ws_srv_{uid}.db")

        s1 = WstunnelState()
        s1.init(db_path, mode="server")
        s1.db().set_server_config(
            bind_url="wss://0.0.0.0:443",
            tls_certificate=certs["cert"],
            tls_private_key=certs["key"],
        )
        s1.db().add_restriction("target", "127.0.0.1:51820")
        s1.db().add_restriction("path_prefix", "ghost")
        s1.close()

        db = WstunnelDB(db_path)
        cfg = db.get_server_config()
        rests = db.list_restrictions()

        assert cfg["bind_url"] == "wss://0.0.0.0:443"
        assert cfg["tls_certificate"] == certs["cert"]
        assert len(rests) == 2
        db.close()

        for ext in ("", "-wal", "-shm"):
            p = db_path + ext
            if os.path.exists(p):
                os.remove(p)


@pytest.mark.docker
class TestSelfSignedTLS:
    """Self-signed certificate via WstunnelState → server starts → cert active."""

    # noinspection PyTypeChecker,PyUnresolvedReferences
    def test_cert_in_tls_handshake(self, uid, certs):
        """Start server from DB config, verify CN=localhost via openssl."""
        db_path = os.path.join(tempfile.gettempdir(), f"ws_tls_{uid}.db")

        state = WstunnelState()
        state.init(db_path, mode="server")
        state.db().set_server_config(
            bind_url="wss://0.0.0.0:8448",
            tls_certificate=certs["cert"],
            tls_private_key=certs["key"],
        )
        state.start(log_level=LogLevel.INFO)
        time.sleep(1)

        try:
            assert wait_for_port(8448), "Server did not start"

            proc = subprocess.run(
                ["openssl", "s_client", "-connect", "127.0.0.1:8448",
                 "-servername", "localhost"],
                input=b"", capture_output=True, timeout=5,
            )
            output = proc.stdout.decode() + proc.stderr.decode()
            assert "CN=localhost" in output or "CN = localhost" in output
        finally:
            state.stop()
            state.close()
            for ext in ("", "-wal", "-shm"):
                p = db_path + ext
                if os.path.exists(p):
                    os.remove(p)

    def test_state_server_start_stop(self, uid, certs):
        """Server lifecycle: DB config → start → running → stop → stopped."""
        db_path = os.path.join(tempfile.gettempdir(), f"ws_lifecycle_{uid}.db")

        state = WstunnelState()
        state.init(db_path, mode="server")
        state.db().set_server_config(
            bind_url="wss://0.0.0.0:8449",
            tls_certificate=certs["cert"],
            tls_private_key=certs["key"],
        )
        state.db().add_restriction("target", "127.0.0.1:9993")
        state.start(log_level=LogLevel.INFO)

        status = state.get_status()
        assert status["status"] == "started"
        assert status["is_running"] is True
        time.sleep(1)

        state.stop()
        status = state.get_status()
        assert status["status"] == "stopped"

        state.close()
        for ext in ("", "-wal", "-shm"):
            p = db_path + ext
            if os.path.exists(p):
                os.remove(p)
