# CI/CD — firewall-bridge

| Workflow                      | Trigger                                     | Jobs                                                                   | Output                            |
|-------------------------------|---------------------------------------------|------------------------------------------------------------------------|-----------------------------------|
| `test-firewall-bridge.yml`    | `dev/firewall-bridge` push, `workflow_call` | `test-rust` (Docker cargo test), `test-python` (Docker test_runner.py) | test-results artifact             |
| `build-firewall-bridge.yml`   | `dev/firewall-bridge` push, `workflow_call` | `build-linux-amd64`, `build-linux-arm64`                               | .so + .h + .sha256 artifacts      |
| `publish-firewall-bridge.yml` | `publish-vendor-firewall-bridge-v*` tag     | `test` → `build` → `publish`                                           | dev/vendor branch (amd64 + arm64) |

## Flow

```
Branch push (dev/firewall-bridge):
  ├── test-firewall-bridge.yml    (Rust unit + Python integration)
  └── build-firewall-bridge.yml   (amd64 + arm64 → artifact upload)

Vendor tag (publish-vendor-firewall-bridge-v*):
  └── publish-firewall-bridge.yml
        ├── test    (workflow_call → test-firewall-bridge.yml)
        ├── build   (workflow_call → build-firewall-bridge.yml)
        └── publish (download artifacts → organize → push to dev/vendor)
```

## Artifacts

| Name                          | Contents                                     | Retention |
|-------------------------------|----------------------------------------------|-----------|
| `test-results`                | pytest output, coverage                      | 30 days   |
| `firewall-bridge-linux-amd64` | .so, .h, .sha256, firewall_bridge/*.py       | 90 days   |
| `firewall-bridge-linux-arm64` | .so, .h, .sha256, firewall_bridge/*.py       | 90 days   |

## Vendor Directory Structure (dev/vendor branch)

```
firewall-bridge/
├── VERSION
├── linux-amd64/
│   ├── libfirewall_bridge_linux.so
│   ├── libfirewall_bridge_linux.so.sha256
│   ├── firewall_bridge_linux.h
│   └── firewall_bridge/
│       ├── __init__.py
│       ├── _ffi.py
│       ├── client.py
│       ├── models.py
│       └── types.py
└── linux-arm64/
    ├── libfirewall_bridge_linux.so
    ├── libfirewall_bridge_linux.so.sha256
    ├── firewall_bridge_linux.h
    └── firewall_bridge/
        └── ...
```

## Notes

- `dist/` is not used — build artifacts flow through GitHub Actions artifacts only
- Vendor artifacts are published to `dev/vendor` branch, not as GitHub Releases
- Each publish overwrites the previous version — version history lives in git commits