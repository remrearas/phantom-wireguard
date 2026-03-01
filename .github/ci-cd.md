# CI/CD — firewall-bridge

| Workflow                      | Trigger                                     | Jobs                                                                   | Output                             |
|-------------------------------|---------------------------------------------|------------------------------------------------------------------------|------------------------------------|
| `test-firewall-bridge.yml`    | `dev/firewall-bridge` push, `workflow_call` | `test-rust` (Docker cargo test), `test-python` (Docker test_runner.py) | test-results artifact              |
| `build-firewall-bridge.yml`   | `dev/firewall-bridge` push, `workflow_call` | `build-linux-amd64`, `build-linux-arm64`                               | .so + .h + .sha256 artifacts       |
| `publish-firewall-bridge.yml` | `firewall-bridge-release-v*` tag            | `test` → `build` → `package`                                           | GitHub Release (amd64 + arm64 zip) |

## Flow

```
Branch push (dev/firewall-bridge):
  ├── test-firewall-bridge.yml    (Rust unit + Python integration)
  └── build-firewall-bridge.yml   (amd64 + arm64 → artifact upload)

Release tag (firewall-bridge-release-v*):
  └── publish-firewall-bridge.yml
        ├── test   (workflow_call → test-firewall-bridge.yml)
        ├── build  (workflow_call → build-firewall-bridge.yml)
        └── package (download build artifacts → zip + Python wrapper → gh release create)
```

## Artifacts

| Name | Contents | Retention |
|------|----------|-----------|
| `test-results` | pytest output, coverage | 30 days |
| `firewall-bridge-linux-amd64` | .so, .h, .sha256, firewall_bridge/*.py | 90 days |
| `firewall-bridge-linux-arm64` | .so, .h, .sha256, firewall_bridge/*.py | 90 days |

## Release Package Contents

```
firewall-bridge-vX.Y.Z-linux-{amd64,arm64}.zip
├── libfirewall_bridge_linux.so
├── libfirewall_bridge_linux.so.sha256
├── firewall_bridge_linux.h
└── firewall_bridge/
    ├── __init__.py
    ├── _ffi.py
    ├── client.py
    ├── models.py
    └── types.py
```

## Notes

- `dist/` is not used — build artifacts flow through GitHub Actions artifacts only
- Release packages are assembled from build artifacts, not from branch contents