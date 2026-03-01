#!/bin/bash
# Exit server — generates ALL keys (server + client), starts WireGuard,
# outputs standard client config (external VPN service provider format).

set -e

WG_PORT="${WG_PORT:-51820}"
SERVER_IP="10.0.2.1/24"
CLIENT_IP="10.0.2.2/24"

# Server keys
SERVER_PRIV=$(wg genkey)
SERVER_PUB=$(echo "$SERVER_PRIV" | wg pubkey)

# Client keys (server generates both sides, like VPN providers do)
CLIENT_PRIV=$(wg genkey)
CLIENT_PUB=$(echo "$CLIENT_PRIV" | wg pubkey)
PSK=$(wg genpsk)

# Server config — already knows the client
cat > /etc/wireguard/wg0.conf <<EOF
[Interface]
PrivateKey = ${SERVER_PRIV}
ListenPort = ${WG_PORT}
Address = ${SERVER_IP}

[Peer]
PublicKey = ${CLIENT_PUB}
PresharedKey = ${PSK}
AllowedIPs = 10.0.2.2/32, 10.0.1.0/24
EOF

wg-quick up wg0
sysctl -w net.ipv4.ip_forward=1 > /dev/null

# Client config — standard WireGuard format from external VPN provider
mkdir -p /config
cat > /config/client.conf <<EOF
[Interface]
PrivateKey = ${CLIENT_PRIV}
Address = ${CLIENT_IP}

[Peer]
PublicKey = ${SERVER_PUB}
PresharedKey = ${PSK}
Endpoint = __EXIT_SERVER_IP__:${WG_PORT}
AllowedIPs = 10.0.2.0/24
PersistentKeepalive = 25
EOF

echo "EXIT_READY"
echo "Server: wg0=${SERVER_IP} listen=${WG_PORT}"
sleep infinity