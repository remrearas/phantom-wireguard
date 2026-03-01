# CI/CD — wstunnel-bridge

| Workflow                        | Trigger                                     | Jobs                                  | Output                             |
|---------------------------------|---------------------------------------------|---------------------------------------|------------------------------------|
| `test-wstunnel-bridge.yml`      | `dev/wstunnel-bridge` push, `workflow_call` | `test-python` (Docker test_runner.py) | test-results artifact              |
| `fetch-wstunnel-artifacts.yaml` | `fetch-wstunnel-artifacts-*` tag            | `fetch-and-publish`                   | dist/ + wstunnel_bridge/ (commit)  |
| `publish-wstunnel-bridge.yml`   | `wstunnel-bridge-release-v*` tag            | `test` → `package`                    | GitHub Release (amd64 + arm64 zip) |

## Flow

```
Branch push (dev/wstunnel-bridge):
  └── test-wstunnel-bridge.yml    (unit + integration via test_runner.py)

Fetch tag (fetch-wstunnel-artifacts-*):
  └── fetch-wstunnel-artifacts.yaml
        └── Download .so from ARAS-Workspace/wstunnel → dist/ commit

Release tag (wstunnel-bridge-release-v*):
  └── publish-wstunnel-bridge.yml
        ├── test    (workflow_call → test-wstunnel-bridge.yml)
        └── package (dist/ → zip + Python wrapper → gh release create)
```

## Artifacts

| Name           | Contents                     | Retention |
|----------------|------------------------------|-----------|
| `test-results` | pytest output, coverage HTML | 30 days   |

## Release Package Contents

```
wstunnel-bridge-vX.Y.Z-linux-{amd64,arm64}.zip
├── libwstunnel_bridge_linux.so
├── libwstunnel_bridge_linux.so.sha256
└── wstunnel_bridge/
    ├── __init__.py
    ├── _ffi.py
    ├── client.py
    ├── db.py
    ├── server.py
    ├── state.py
    └── types.py
```

## Notes

- `.so` is built in external repo (ARAS-Workspace/wstunnel), fetched via `fetch-wstunnel-artifacts.yaml`
- `dist/` is committed to branch (unlike firewall/wireguard bridges which use artifact-only flow)
- Release packages are assembled from branch `dist/` contents
- No build workflow needed — build happens in external repo