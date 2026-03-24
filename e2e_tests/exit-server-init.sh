#!/bin/bash
# Exit server (dual-stack) — generates ALL keys (server + client), starts
# WireGuard, outputs standard client configs (IPv4 + IPv6).
#
# Subnet: 10.0.2.0/24 (exit tunnel IPv4), fd00:10:2::/64 (exit tunnel IPv6)
# Listen: 51821 (exit-server port)

set -e

WG_PORT="${WG_PORT:-51821}"

# Server keys
SERVER_PRIV=$(wg genkey)
SERVER_PUB=$(echo "$SERVER_PRIV" | wg pubkey)

# Client keys (server generates both sides, like VPN providers do)
CLIENT_PRIV=$(wg genkey)
CLIENT_PUB=$(echo "$CLIENT_PRIV" | wg pubkey)
PSK=$(wg genpsk)

# Server config — dual-stack
cat > /etc/wireguard/wg0.conf <<EOF
[Interface]
PrivateKey = ${SERVER_PRIV}
ListenPort = ${WG_PORT}
Address = 10.0.2.1/24, fd00:10:2::1/64

[Peer]
PublicKey = ${CLIENT_PUB}
PresharedKey = ${PSK}
AllowedIPs = 10.0.2.2/32, fd00:10:2::2/128, 10.0.1.0/24, fd00:10:1::/64
EOF

wg-quick up wg0
sysctl -w net.ipv4.ip_forward=1 > /dev/null
sysctl -w net.ipv6.conf.all.forwarding=1 > /dev/null

# Client configs — standard WireGuard format
mkdir -p /config

# IPv4 config (existing behavior)
cat > /config/client.conf <<EOF
[Interface]
PrivateKey = ${CLIENT_PRIV}
Address = 10.0.2.2/24

[Peer]
PublicKey = ${SERVER_PUB}
PresharedKey = ${PSK}
Endpoint = __EXIT_SERVER_IP__:${WG_PORT}
AllowedIPs = 10.0.2.0/24
PersistentKeepalive = 25
EOF

# IPv6 config
cat > /config/client-v6.conf <<EOF
[Interface]
PrivateKey = ${CLIENT_PRIV}
Address = fd00:10:2::2/64

[Peer]
PublicKey = ${SERVER_PUB}
PresharedKey = ${PSK}
Endpoint = [__EXIT_SERVER_IP6__]:${WG_PORT}
AllowedIPs = fd00:10:2::/64
PersistentKeepalive = 25
EOF

echo "EXIT_READY"
echo "Server: wg0=10.0.2.1/24+fd00:10:2::1/64 listen=${WG_PORT}"
sleep infinity
