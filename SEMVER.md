# Phantom-WG Semantic Versioning

## Product Versions

Two product lines exist under the Phantom-WG umbrella:

| Product               | Description                                   | Branch |
|-----------------------|-----------------------------------------------|--------|
| **Phantom-WG Modern** | Full platform (daemon + SPA + auth + bridges) | main   |
| **Phantom-WG Retro**  | Legacy core-only release                      | retro  |

## Version Hierarchy

**Phantom-WG Modern version = Phantom Daemon version.**

The daemon is the central package that defines the product version.
All other components are dependencies with their own independent semver cycles.

```
Phantom-WG Modern vX.Y.Z
  └── Phantom Daemon vX.Y.Z             ← product version source
        ├── auth-service vA.B.C         ← dependency
        ├── wireguard-go-bridge vA.B.C  ← dependency
        ├── firewall-bridge vA.B.C      ← dependency
        ├── react-spa (build artifact)  ← bundled with release
        └── nginx config                ← bundled with release
```

## Daemon Version (Product Version)

The daemon version follows standard semver and directly maps to the
Phantom-WG Modern release version:

- **Major** — Breaking changes, architectural shifts
- **Minor** — New features, new API endpoints
- **Patch** — Bug fixes, security patches

The daemon version is the single source of truth for the product version.
When a new Phantom-WG Modern release is cut, it carries the daemon version.

### Where it lives

- `phantom_daemon/__init__.py` → `__version__`
- `GET /api/core/hello` → `version` field
- Dashboard status card → displayed to the user

## Dependency Versions

Dependencies maintain their own semver independently. Their versions
change frequently during development. A dependency version bump does
**not** automatically bump the daemon (product) version.

A daemon version bump happens when the integrated product — daemon +
dependencies — reaches a new release milestone.

### Dependencies

| Component               | Versioning           | Branch                   |
|-------------------------|----------------------|--------------------------|
| **auth-service**        | semver               | dev/auth-service         |
| **wireguard-go-bridge** | semver               | dev/wireguard-go-bridge  |
| **firewall-bridge**     | semver               | dev/firewall-bridge      |
| **compose-bridge**      | semver               | dev/tests/compose-bridge |
| **react-spa**           | package.json version | dev/daemon (embedded)    |

### Vendor Distribution

Bridge binaries are distributed via `vendor.phantom.tc` (Cloudflare R2).
Each bridge has its own publish workflow that uploads versioned artifacts.
The daemon Dockerfile fetches the relevant version or `latest` path at build time.

```
vendor.phantom.tc/
├── firewall-bridge/{version}/linux-{arch}.zip
└── wireguard-go-bridge/{version}/linux-{arch}.zip
```

## Retro Version

Phantom-WG Retro uses its own independent version line (`core-vX.Y.Z`)
and is maintained on the `retro` branch. It does not follow the daemon
version hierarchy described above.
