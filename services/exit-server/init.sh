#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────
# Development exit server for multihop testing (dual-stack).
#
# Generates WireGuard keypair, starts wg0, and writes client
# configs to /config/ with the real container IPs as endpoints.
# The daemon can read these configs and import them.
# ──────────────────────────────────────────────────────────────────

set -euo pipefail

WG_PORT="${WG_PORT:-51820}"
EXIT_IP="${EXIT_IP:-172.28.0.100}"
EXIT_IP6="${EXIT_IP6:-fd00:d0ce::100}"

# ── Generate keys ────────────────────────────────────────────────

SERVER_PRIV=$(wg genkey)
SERVER_PUB=$(echo "$SERVER_PRIV" | wg pubkey)
CLIENT_PRIV=$(wg genkey)
CLIENT_PUB=$(echo "$CLIENT_PRIV" | wg pubkey)
PSK=$(wg genpsk)

echo "Exit server keys generated."
echo "  Server pub: $SERVER_PUB"
echo "  Client pub: $CLIENT_PUB"
echo "  Endpoint v4: ${EXIT_IP}:${WG_PORT}"
echo "  Endpoint v6: [${EXIT_IP6}]:${WG_PORT}"

# ── Server WireGuard config ─────────────────────────────────────

cat > /etc/wireguard/wg0.conf <<EOF
[Interface]
PrivateKey = ${SERVER_PRIV}
ListenPort = ${WG_PORT}
Address = 10.0.2.1/24, fd10:0:2::1/64

[Peer]
PublicKey = ${CLIENT_PUB}
PresharedKey = ${PSK}
AllowedIPs = 10.0.2.2/32, fd10:0:2::2/128, 10.0.1.0/24
EOF

wg-quick up wg0

# ── Client configs (for daemon to import) ────────────────────────

mkdir -p /config

# IPv4 endpoint config
cat > /config/client.conf <<EOF
[Interface]
PrivateKey = ${CLIENT_PRIV}
Address = 10.0.2.2/24, fd10:0:2::2/64

[Peer]
PublicKey = ${SERVER_PUB}
PresharedKey = ${PSK}
Endpoint = ${EXIT_IP}:${WG_PORT}
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
EOF

# IPv6 endpoint config
cat > /config/client-v6.conf <<EOF
[Interface]
PrivateKey = ${CLIENT_PRIV}
Address = 10.0.2.2/24, fd10:0:2::2/64

[Peer]
PublicKey = ${SERVER_PUB}
PresharedKey = ${PSK}
Endpoint = [${EXIT_IP6}]:${WG_PORT}
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
EOF

echo "EXIT_READY"
exec sleep infinity
