# CI/CD — dev/vendor

| Workflow                    | Trigger                          | Jobs      | Output                                  |
|-----------------------------|----------------------------------|-----------|-----------------------------------------|
| `publish-vendor-pack.yml`   | `publish-vendor-pack-v*` tag     | `publish` | GitHub Release (amd64 + arm64 zip)      |

## Flow

```
Vendor pack tag (publish-vendor-pack-v*):
  └── publish-vendor-pack.yml
        └── publish (packager.py → dist/ → gh release create)
```

## Vendor Pack Contents

```
vendor-pack-vX.Y.Z-linux-{amd64,arm64}.zip
├── wireguard_go_bridge/
│   ├── VERSION
│   ├── __init__.py, _ffi.py, client.py, types.py
│   ├── wireguard_go_bridge.so
│   └── wireguard_go_bridge.so.sha256
├── firewall_bridge/
│   ├── VERSION
│   ├── __init__.py, _ffi.py, client.py, models.py, types.py
│   ├── libfirewall_bridge_linux.so
│   ├── libfirewall_bridge_linux.so.sha256
│   └── firewall_bridge_linux.h
└── wstunnel_bridge/
    ├── VERSION
    ├── __init__.py, _ffi.py, client.py, db.py, server.py, state.py, types.py
    ├── libwstunnel_bridge_linux.so
    └── libwstunnel_bridge_linux.so.sha256
```

## Notes

- Bridge artifacts are sourced from this branch (pushed by each bridge's publish workflow)
- `packager.py` validates sources, verifies checksums, builds per-arch zip files
- Each Python package contains its .so — `_ffi.py` finds it via sibling path
- Daemon downloads the correct arch zip once during setup