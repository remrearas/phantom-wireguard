# CI/CD — wireguard-go-bridge

| Workflow                          | Trigger                                         | Jobs                                                               | Output                            |
|-----------------------------------|------------------------------------------------ |--------------------------------------------------------------------|---------------------------------  |
| `test-wireguard-go-bridge.yml`    | `dev/wireguard-go-bridge` push, `workflow_call` | `test` (Docker unit+integration), `test-netns` (network namespace) | test-results artifact             |
| `build-wireguard-go-bridge.yml`   | `dev/wireguard-go-bridge` push, `workflow_call` | `build-linux-amd64`, `build-linux-arm64`                           | .so + .h + .sha256 artifacts      |
| `publish-wireguard-go-bridge.yml` | `publish-vendor-wireguard-go-bridge-v*` tag     | `test` → `build` → `publish`                                      | dev/vendor branch (amd64 + arm64) |

## Flow

```
Branch push (dev/wireguard-go-bridge):
  ├── test-wireguard-go-bridge.yml    (unit + integration + netns)
  └── build-wireguard-go-bridge.yml   (amd64 + arm64 → artifact upload)

Vendor tag (publish-vendor-wireguard-go-bridge-v*):
  └── publish-wireguard-go-bridge.yml
        ├── test    (workflow_call → test-wireguard-go-bridge.yml)
        ├── build   (workflow_call → build-wireguard-go-bridge.yml)
        └── publish (download artifacts → organize → push to dev/vendor)
```

## Artifacts

| Name                              | Contents                | Retention |
|-----------------------------------|-------------------------|-----------|
| `test-results`                    | pytest output, coverage | 30 days   |
| `wireguard-go-bridge-linux-amd64` | .so, .h, .sha256        | 90 days   |
| `wireguard-go-bridge-linux-arm64` | .so, .h, .sha256        | 90 days   |

## Vendor Directory Structure (dev/vendor branch)

```
wireguard-go-bridge/
├── VERSION
├── linux-amd64/
│   ├── wireguard_go_bridge.so
│   ├── wireguard_go_bridge.so.sha256
│   └── wireguard_go_bridge/
│       ├── __init__.py
│       ├── _ffi.py
│       ├── client.py
│       └── types.py
└── linux-arm64/
    ├── wireguard_go_bridge.so
    ├── wireguard_go_bridge.so.sha256
    └── wireguard_go_bridge/
        └── ...
```

## Notes

- `dist/` is not used — build artifacts flow through GitHub Actions artifacts only
- Vendor artifacts are published to `dev/vendor` branch, not as GitHub Releases
- Each publish overwrites the previous version — version history lives in git commits