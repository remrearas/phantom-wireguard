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
All command output streams live to stdout via Rich Console.
"""

import subprocess

from rich.console import Console
from rich.panel import Panel

console = Console(no_color=True)

CLIENT_CONTAINER = "fw-client"

ACTORS = {
    "bridge": "BRIDGE  ",
    "exit":   "EXIT    ",
    "client": "CLIENT  ",
    "verify": "VERIFY  ",
    "db":     "DB      ",
}


def _log(actor: str, msg: str) -> None:
    console.print(f"  {ACTORS[actor]} {msg}")


def phase_banner(num: int, title: str) -> None:
    console.print()
    console.print(Panel(title, title=f"PHASE {num}", width=64))
    console.print()


def result_banner(passed: bool = True) -> None:
    text = "ALL PHASES PASSED" if passed else "FAILED"
    console.print()
    console.print(Panel(text, width=64))
    console.print()


# ---- Local shell (live output) ----

def sh(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    console.print(f"  $ {cmd}")
    r = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, check=False,
    )
    if r.stdout and r.stdout.strip():
        for line in r.stdout.strip().splitlines():
            console.print(f"    > {line}")
    if r.stderr and r.stderr.strip():
        for line in r.stderr.strip().splitlines():
            console.print(f"    ERR> {line}")
    if check and r.returncode != 0:
        console.print(f"  exit={r.returncode}")
    return r


# ---- Remote exec on client container via Docker SDK ----

def _get_docker_client():
    import docker
    return docker.from_env()


def client_exec(cmd: str, check: bool = True) -> tuple[int, str]:
    console.print(f"  CLIENT $ {cmd}")
    dc = _get_docker_client()
    container = dc.containers.get(CLIENT_CONTAINER)
    r = container.exec_run(["sh", "-c", cmd])
    output = r.output.decode("utf-8", errors="replace")
    if output.strip():
        for line in output.strip().splitlines():
            console.print(f"    CLIENT > {line}")
    if check and r.exit_code != 0:
        console.print(f"  CLIENT exit={r.exit_code}")
    return r.exit_code, output


def client_write_file(path: str, content: str) -> None:
    import base64
    encoded = base64.b64encode(content.encode()).decode()
    client_exec(f"echo {encoded} | base64 -d > {path}")
