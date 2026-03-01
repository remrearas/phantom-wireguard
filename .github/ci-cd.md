# CI/CD — wireguard-go-bridge

| Workflow                          | Trigger                                         | Jobs                                                               | Output                             |
|-----------------------------------|-------------------------------------------------|--------------------------------------------------------------------|------------------------------------|
| `test-wireguard-go-bridge.yml`    | `dev/wireguard-go-bridge` push, `workflow_call` | `test` (Docker unit+integration), `test-netns` (network namespace) | test-results artifact              |
| `build-wireguard-go-bridge.yml`   | `dev/wireguard-go-bridge` push, `workflow_call` | `build-linux-amd64`, `build-linux-arm64`                           | .so + .h + .sha256 artifacts       |
| `publish-wireguard-go-bridge.yml` | `wireguard-go-bridge-release-v*` tag            | `test` → `build` → `package`                                       | GitHub Release (amd64 + arm64 zip) |

## Flow

```
Branch push (dev/wireguard-go-bridge):
  ├── test-wireguard-go-bridge.yml    (unit + integration + netns)
  └── build-wireguard-go-bridge.yml   (amd64 + arm64 → artifact upload)

Release tag (wireguard-go-bridge-release-v*):
  └── publish-wireguard-go-bridge.yml
        ├── test   (workflow_call → test-wireguard-go-bridge.yml)
        ├── build  (workflow_call → build-wireguard-go-bridge.yml)
        └── package (download artifacts → zip + Python wrapper → gh release create)
```

## Artifacts

| Name                              | Contents                | Retention |
|-----------------------------------|-------------------------|-----------|
| `test-results`                    | pytest output, coverage | 30 days   |
| `wireguard-go-bridge-linux-amd64` | .so, .h, .sha256        | 90 days   |
| `wireguard-go-bridge-linux-arm64` | .so, .h, .sha256        | 90 days   |

## Release Package Contents

```
wireguard-go-bridge-vX.Y.Z-linux-{amd64,arm64}.zip
├── wireguard_go_bridge.so
├── wireguard_go_bridge.so.sha256
└── wireguard_go_bridge/
    ├── __init__.py
    ├── _ffi.py
    ├── client.py
    └── types.py
```

## Notes

- `dist/` is not used — build artifacts flow through GitHub Actions artifacts only
- Release packages are assembled from build artifacts, not from branch contents