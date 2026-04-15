# compose-bridge

Python FFI over the Docker Compose v5 SDK. Drives compose projects
programmatically (`up` / `down` / `exec` / `logs` / `ps`) without
shelling out to `docker compose`.

Internal test-orchestration tool for the Phantom-WG ecosystem. Not
shipped to end users and not part of the public vendor pack.

## Purpose

Standing up a compose project on the Python side via the Docker SDK
and sending programmatic `exec` calls against it during a test run
was not directly possible. The Docker SDK operates at single-container
granularity and has no compose orchestration surface. To close that
gap, compose-bridge exposes the Go-side Docker Compose SDK to Python
over FFI.

## Used by

- [`dev/daemon`](https://github.com/ARAS-Workspace/phantom-wg/tree/dev/daemon)
  — multihop, chaos, and scenario E2E tests, pulled via
  [`tools/dev.sh fetch-compose-bridge`](https://github.com/ARAS-Workspace/phantom-wg/blob/dev/daemon/tools/lib/test.sh).
- [`dev/firewall-bridge`](https://github.com/ARAS-Workspace/phantom-wg/tree/dev/firewall-bridge)
  — multihop v4/v6 E2E tests, pulled via
  [`fetch_compose_bridge.sh`](https://github.com/ARAS-Workspace/phantom-wg/blob/dev/firewall-bridge/fetch_compose_bridge.sh).

Both consumers track the latest successful publish run.

## Usage

```python
from compose_bridge import ComposeBridge

with ComposeBridge("docker-compose.yml", project_name="mh-test") as bridge:
    bridge.up()

    result = bridge.exec("daemon", ["pytest", "-v"])
    assert result.exit_code == 0

    bridge.down()
```

A 6-char hex suffix is appended to `project_name` at construction time
so parallel test runs never collide on Docker namespaces.

Available methods: `up`, `down`, `ps`, `exec`, `logs`, `version`. All
errors raise typed exceptions (`BridgeError`, `ProjectUpError`,
`ExecError`, …) with the Go-side last-error message attached.

## Development & testing

```bash
python test_runner.py --build
python test_runner.py
```

`test_runner.py` stands up a tiny `alpine` compose service and
exercises every FFI export end-to-end.

## License

AGPL-3.0 — see [LICENSE](LICENSE).
