# CI/CD — wireguard-go-bridge

## Workflows

| Workflow                          | Trigger                                    | Jobs                                     | Output                         |
|-----------------------------------|--------------------------------------------|------------------------------------------|--------------------------------|
| `test-wireguard-go-bridge.yml`    | push (`.github/` ignored), `workflow_call` | `test` (Docker unit+integration)         | test-results artifact          |
| `build-wireguard-go-bridge.yml`   | push (`.github/` ignored), `workflow_call` | `build-linux-amd64`, `build-linux-arm64` | .so + .sha256 artifacts        |
| `publish-wireguard-go-bridge.yml` | `workflow_dispatch`                        | `version` → `test` → `build` → `publish` | R2 upload (versioned + latest) |

## Flow

```
Branch push (dev/wireguard-go-bridge, .github/ ignored):
  ├── test-wireguard-go-bridge.yml   (unit + integration via test_runner.py)
  └── build-wireguard-go-bridge.yml  (amd64 + arm64 → artifact upload)

Publish (workflow_dispatch):
  └── publish-wireguard-go-bridge.yml
        ├── version   (extract from wireguard_go_bridge/__init__.py)
        ├── test      (workflow_call → test-wireguard-go-bridge.yml)
        ├── build     (workflow_call → build-wireguard-go-bridge.yml)
        └── publish   (self-hosted, rclone → R2)
```

## Version

Single source of truth: `wireguard_go_bridge/__init__.py` → `__version__`

Publish workflow reads version automatically.

## Trigger

```bash
.github/scripts/publish.sh
```

No arguments — version is read from source.

## Artifacts

| Name                              | Contents                | Retention |
|-----------------------------------|-------------------------|-----------|
| `test-results`                    | pytest output, coverage | 30 days   |
| `wireguard-go-bridge-linux-amd64` | .so, .sha256            | 90 days   |
| `wireguard-go-bridge-linux-arm64` | .so, .sha256            | 90 days   |

## R2 Storage

Bucket: `phantom-vendor` — Domain: `vendor.phantom.tc`

```
wireguard-go-bridge/
├── v2.1.2/
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
wireguard_go_bridge/
├── __init__.py
├── _ffi.py
├── bridge.py
├── keys.py
├── types.py
├── wireguard_go_bridge.so
├── wireguard_go_bridge.so.sha256
└── VERSION
```

Download:

```
https://vendor.phantom.tc/wireguard-go-bridge/v2.1.2/linux-amd64.zip
https://vendor.phantom.tc/wireguard-go-bridge/latest/linux-arm64.zip
```

## Notes

- `.github/` changes do not trigger test/build on push (paths-ignore)
- Publish runs on self-hosted runner (rclone + R2 remote preconfigured)
- Both versioned and latest paths are updated on each publish
- VERSION file inside zip for runtime version verification
