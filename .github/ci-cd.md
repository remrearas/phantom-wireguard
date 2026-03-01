# CI/CD — wstunnel-bridge

| Workflow                        | Trigger                                     | Jobs                                  | Output                            |
|---------------------------------|---------------------------------------------|---------------------------------------|-----------------------------------|
| `test-wstunnel-bridge.yml`      | `dev/wstunnel-bridge` push, `workflow_call` | `test-python` (Docker test_runner.py) | test-results artifact             |
| `fetch-wstunnel-artifacts.yaml` | `fetch-wstunnel-artifacts-*` tag            | `fetch-and-publish`                   | dist/ + wstunnel_bridge/ (commit) |
| `publish-wstunnel-bridge.yml`   | `publish-vendor-wstunnel-bridge-v*` tag     | `test` → `publish`                    | dev/vendor branch (amd64 + arm64) |

## Flow

```
Branch push (dev/wstunnel-bridge):
  └── test-wstunnel-bridge.yml    (unit + integration via test_runner.py)

Fetch tag (fetch-wstunnel-artifacts-*):
  └── fetch-wstunnel-artifacts.yaml
        └── Download .so from ARAS-Workspace/wstunnel → dist/ commit

Vendor tag (publish-vendor-wstunnel-bridge-v*):
  └── publish-wstunnel-bridge.yml
        ├── test    (workflow_call → test-wstunnel-bridge.yml)
        └── publish (dist/ + Python wrapper → push to dev/vendor)
```

## Artifacts

| Name           | Contents                     | Retention |
|----------------|------------------------------|-----------|
| `test-results` | pytest output, coverage HTML | 30 days   |

## Vendor Directory Structure (dev/vendor branch)

```
wstunnel-bridge/
├── VERSION
├── linux-amd64/
│   ├── libwstunnel_bridge_linux.so
│   ├── libwstunnel_bridge_linux.so.sha256
│   └── wstunnel_bridge/
│       ├── __init__.py
│       ├── _ffi.py
│       ├── client.py
│       ├── db.py
│       ├── server.py
│       ├── state.py
│       └── types.py
└── linux-arm64/
    ├── libwstunnel_bridge_linux.so
    ├── libwstunnel_bridge_linux.so.sha256
    └── wstunnel_bridge/
        └── ...
```

## Notes

- `.so` is built in external repo (ARAS-Workspace/wstunnel), fetched via `fetch-wstunnel-artifacts.yaml`
- `dist/` is committed to branch (unlike wireguard-go-bridge which uses artifact-only flow)
- Vendor artifacts are published to `dev/vendor` branch, not as GitHub Releases
- Each publish overwrites the previous version — version history lives in git commits