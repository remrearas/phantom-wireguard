# Environment Variables

All variables are optional. Defaults are production-safe except where noted.

## Server

| Variable         | Default   | Type   | Description                                                |
|------------------|-----------|--------|------------------------------------------------------------|
| `AUTH_HOST`      | `0.0.0.0` | string | Bind address                                               |
| `AUTH_PORT`      | `8443`    | int    | Listen port                                                |
| `AUTH_LOG_LEVEL` | `info`    | string | Uvicorn log level (`debug` · `info` · `warning` · `error`) |

## Paths

| Variable           | Default                 | Type | Description                                                            |
|--------------------|-------------------------|------|------------------------------------------------------------------------|
| `AUTH_DB_DIR`      | `/var/lib/phantom/auth` | path | Directory containing `auth.db` — must exist before startup             |
| `AUTH_SECRETS_DIR` | `/run/secrets`          | path | Directory containing key files (`auth_signing_key`, `auth_verify_key`) |

## Proxy

| Variable              | Default                               | Type        | Description                                                    |
|-----------------------|---------------------------------------|-------------|----------------------------------------------------------------|
| `AUTH_PROXY_URL`      | `unix:///var/run/phantom/daemon.sock` | URL         | Daemon target. `unix://` prefix = UDS, otherwise plain HTTP    |
| `AUTH_PROXY_TIMEOUT`  | `30.0`                                | float (s)   | Per-request timeout toward daemon                              |
| `AUTH_PROXY_MAX_BODY` | `65536`                               | int (bytes) | Max forwarded request body — exceeded → `BODY_TOO_LARGE` (413) |

## Token Lifetimes

| Variable                   | Default | Type    | Description                                                              |
|----------------------------|---------|---------|--------------------------------------------------------------------------|
| `AUTH_TOKEN_LIFETIME`      | `86400` | int (s) | Access token validity (24 h)                                             |
| `AUTH_INACTIVITY_TIMEOUT`  | `1800`  | int (s) | Session invalidated after this idle period (30 min) → `SESSION_INACTIVE` |
| `AUTH_MFA_TOKEN_LIFETIME`  | `120`   | int (s) | MFA pending token + password change token validity (2 min)               |
| `AUTH_TOTP_SETUP_LIFETIME` | `300`   | int (s) | TOTP setup token validity (5 min)                                        |

## Rate Limiting

| Variable                 | Default | Type    | Description                                                               |
|--------------------------|---------|---------|---------------------------------------------------------------------------|
| `AUTH_RATE_LIMIT_WINDOW` | `60`    | int (s) | Sliding window duration                                                   |
| `AUTH_RATE_LIMIT_MAX`    | `5`     | int     | Max failed login attempts within window — exceeded → `RATE_LIMITED` (429) |

> Rate limiting applies to `POST /auth/login` only, keyed by client IP (`X-Forwarded-For` → first hop, fallback to direct IP).