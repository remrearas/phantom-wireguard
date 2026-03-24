# CI/CD — firewall-bridge

## Workflows

| Workflow                      | Trigger                                    | Jobs                                     | Output                         |
|-------------------------------|--------------------------------------------|------------------------------------------|--------------------------------|
| `test-firewall-bridge.yml`    | push (`.github/` ignored), `workflow_call` | `test-rust`, `test-python`, `e2e`        | —                              |
| `build-firewall-bridge.yml`   | push (`.github/` ignored), `workflow_call` | `build-linux-amd64`, `build-linux-arm64` | .so + .h + .sha256 artifacts   |
| `publish-firewall-bridge.yml` | `workflow_dispatch`                        | `version` → `test` → `build` → `publish` | R2 upload (versioned + latest) |

## Flow

```
Branch push (dev/firewall-bridge, .github/ ignored):
  ├── test-firewall-bridge.yml
  │     ├── test-rust      (Docker cargo test)
  │     ├── test-python    (Docker SDK unit runner)
  │     └── e2e            (compose-bridge multihop v4/v6)
  └── build-firewall-bridge.yml
        ├── build-linux-amd64  (ubuntu-latest)
        └── build-linux-arm64  (ubuntu-24.04-arm)

Publish (workflow_dispatch):
  └── publish-firewall-bridge.yml
        ├── version   (extract from firewall_bridge/__init__.py)
        ├── test      (workflow_call → test-firewall-bridge.yml)
        ├── build     (workflow_call → build-firewall-bridge.yml)
        └── publish   (self-hosted, rclone → R2)
```

## Version

Single source of truth: `firewall_bridge/__init__.py` → `__version__`

Publish workflow reads version automatically. `Cargo.toml` version is validated to match.

## Trigger

```bash
.github/scripts/publish.sh
```

No arguments — version is read from source.

## Artifacts

| Name                          | Contents                                         | Retention |
|-------------------------------|--------------------------------------------------|-----------|
| `firewall-bridge-linux-amd64` | .so, .h, .sha256, firewall_bridge/*.py, schemas/ | 90 days   |
| `firewall-bridge-linux-arm64` | .so, .h, .sha256, firewall_bridge/*.py, schemas/ | 90 days   |

## R2 Storage

Bucket: `phantom-vendor` — Domain: `vendor.phantom.tc`

```
firewall-bridge/
├── v2.1.3/
│   ├── linux-amd64.zip
│   ├── linux-arm64.zip
│   └── VERSION
└── latest/
    ├── linux-amd64.zip
    ├── linux-arm64.zip
    └── VERSION
```

Each zip contains:

```
firewall_bridge/
├── __init__.py
├── _ffi.py
├── bridge.py
├── db.py
├── models.py
├── presets.py
├── schema.py
├── types.py
├── schemas/
│   └── schema.sql
├── libfirewall_bridge_linux.so
├── libfirewall_bridge_linux.so.sha256
├── firewall_bridge_linux.h
└── VERSION
```

Download:

```
https://vendor.phantom.tc/firewall-bridge/v2.1.3/linux-amd64.zip
https://vendor.phantom.tc/firewall-bridge/latest/linux-arm64.zip
```

## Notes

- `.github/` changes do not trigger test/build on push (paths-ignore)
- Publish runs on self-hosted runner (rclone + R2 remote preconfigured)
- Both versioned and latest paths are updated on each publish
- VERSION file inside zip for runtime version verification
