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

Integration test helpers — runs inside Docker container.
Docker socket mounted for cross-container communication.
All command output streams live to stdout.
"""

import logging
import os
import sqlite3
import subprocess
import sys

log = logging.getLogger("integration")

CLIENT_CONTAINER = "wg-client"


# ---- Local shell (live output) ----

def sh(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    log.info("  $ %s", cmd)
    r = subprocess.run(cmd, shell=True, stdout=sys.stdout, stderr=sys.stderr, text=True, check=False)
    if check and r.returncode != 0:
        log.warning("  exit=%d", r.returncode)
    return r


# ---- Remote exec on client container via Docker SDK ----

def _get_docker_client():
    import docker
    return docker.from_env()


def client_exec(cmd: str, check: bool = True) -> tuple[int, str]:
    log.info("  CLIENT $ %s", cmd)
    dc = _get_docker_client()
    container = dc.containers.get(CLIENT_CONTAINER)
    r = container.exec_run(["sh", "-c", cmd])
    output = r.output.decode("utf-8", errors="replace")
    # Print live
    if output.strip():
        for line in output.strip().splitlines():
            print(f"  CLIENT | {line}", flush=True)
    if check and r.exit_code != 0:
        log.warning("  CLIENT exit=%d", r.exit_code)
    return r.exit_code, output


def client_write_file(path: str, content: str) -> None:
    import base64
    encoded = base64.b64encode(content.encode()).decode()
    client_exec(f"echo {encoded} | base64 -d > {path}")


# ---- device.db ----

def create_device_db(path: str) -> None:
    for suffix in ("", "-shm", "-wal"):
        p = path + suffix
        if os.path.exists(p):
            os.remove(p)
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ipc_state (
            id   INTEGER PRIMARY KEY CHECK (id = 1),
            dump TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()