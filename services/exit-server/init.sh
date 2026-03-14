#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────
# Development exit server for multihop testing.
#
# Generates WireGuard keypair, starts wg0, and writes a client
# config to /config/client.conf with the real container IP as
# the endpoint. The daemon can read this config and import it.
# ──────────────────────────────────────────────────────────────────

set -euo pipefail

WG_PORT="${WG_PORT:-51820}"
EXIT_IP="${EXIT_IP:-172.28.0.100}"

# ── Generate keys ────────────────────────────────────────────────

SERVER_PRIV=$(wg genkey)
SERVER_PUB=$(echo "$SERVER_PRIV" | wg pubkey)
CLIENT_PRIV=$(wg genkey)
CLIENT_PUB=$(echo "$CLIENT_PRIV" | wg pubkey)
PSK=$(wg genpsk)

echo "Exit server keys generated."
echo "  Server pub: $SERVER_PUB"
echo "  Client pub: $CLIENT_PUB"
echo "  Endpoint:   ${EXIT_IP}:${WG_PORT}"

# ── Server WireGuard config ─────────────────────────────────────

cat > /etc/wireguard/wg0.conf <<EOF
[Interface]
PrivateKey = ${SERVER_PRIV}
ListenPort = ${WG_PORT}
Address = 10.0.2.1/24

[Peer]
PublicKey = ${CLIENT_PUB}
PresharedKey = ${PSK}
AllowedIPs = 10.0.2.2/32, 10.0.1.0/24
EOF

wg-quick up wg0

# ── Client config (for daemon to import) ────────────────────────

mkdir -p /config
cat > /config/client.conf <<EOF
[Interface]
PrivateKey = ${CLIENT_PRIV}
Address = 10.0.2.2/24

[Peer]
PublicKey = ${SERVER_PUB}
PresharedKey = ${PSK}
Endpoint = ${EXIT_IP}:${WG_PORT}
AllowedIPs = 10.0.2.0/24
PersistentKeepalive = 25
EOF

echo "EXIT_READY"
exec sleep infinity
