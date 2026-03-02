#!/usr/bin/env bash
# Exit server — WireGuard endpoint with forwarding.
# Generates keys + PSK, configures wg0, enables NAT + forwarding.
# Writes client config to /config/client.conf for test_runner to read.
set -euo pipefail

echo "EXIT_SERVER: generating keys..."
SERVER_PRIVKEY=$(wg genkey)
SERVER_PUBKEY=$(echo "$SERVER_PRIVKEY" | wg pubkey)
CLIENT_PRIVKEY=$(wg genkey)
CLIENT_PUBKEY=$(echo "$CLIENT_PRIVKEY" | wg pubkey)
PSK=$(wg genpsk)

# Server WG interface
ip link add wg0 type wireguard
wg set wg0 \
    listen-port 51821 \
    private-key <(echo "$SERVER_PRIVKEY") \
    peer "$CLIENT_PUBKEY" \
        preshared-key <(echo "$PSK") \
        allowed-ips 10.0.2.2/32,10.0.1.0/24
ip addr add 10.0.2.1/24 dev wg0
ip link set wg0 up

# Enable forwarding + NAT
sysctl -w net.ipv4.ip_forward=1 > /dev/null
iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
iptables -A FORWARD -i wg0 -j ACCEPT
iptables -A FORWARD -o wg0 -m state --state RELATED,ESTABLISHED -j ACCEPT

echo "EXIT_SERVER: wg0 up (10.0.2.1/24, :51821)"
wg show wg0

# Client config file (test_runner reads + replaces __EXIT_SERVER_IP__ at runtime)
mkdir -p /config
cat > /config/client.conf <<EOF
[Interface]
PrivateKey = ${CLIENT_PRIVKEY}
Address = 10.0.2.2/24

[Peer]
PublicKey = ${SERVER_PUBKEY}
PresharedKey = ${PSK}
Endpoint = __EXIT_SERVER_IP__:51821
AllowedIPs = 10.0.2.0/24
PersistentKeepalive = 25
EOF

echo "EXIT_READY"

exec sleep infinity
