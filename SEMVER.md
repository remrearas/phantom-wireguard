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
Phantom-WG Modern v1.0.0
  └── Phantom Daemon v1.0.0             ← product version source
        ├── auth-service v1.1.1         ← dependency
        ├── wireguard-go-bridge v2.1.1  ← dependency
        ├── firewall-bridge v2.1.0      ← dependency
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

Bridge binaries are distributed via `vendor-artifacts.phantom.tc`.
Each bridge publishes versioned artifacts that the daemon Dockerfile
fetches at build time. The vendor store lives on the `dev/vendor` branch.

## Retro Version

Phantom-WG Retro uses its own independent version line (`core-vX.Y.Z`)
and is maintained on the `retro` branch. It does not follow the daemon
version hierarchy described above.
