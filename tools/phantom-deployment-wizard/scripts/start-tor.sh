#!/bin/bash
# ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
# ██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
# ██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
# ██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
# ██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
# ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
# Copyright (c) 2025 Rıza Emre ARAS
#
set -e

# Setup iptables BEFORE starting Tor to avoid Tor-over-Tor loop
echo "Configuring transparent proxy with iptables..."

# Don't redirect loopback traffic
iptables -t nat -A OUTPUT -o lo -j RETURN

# Don't redirect to localhost
iptables -t nat -A OUTPUT -d 127.0.0.0/8 -j RETURN

# Don't redirect to reserved IP ranges (RFC 1918)
iptables -t nat -A OUTPUT -d 10.0.0.0/8 -j RETURN
iptables -t nat -A OUTPUT -d 172.16.0.0/12 -j RETURN
iptables -t nat -A OUTPUT -d 192.168.0.0/16 -j RETURN

# Get Tor user UID (will be used for bypass)
TOR_UID=$(id -u debian-tor 2>/dev/null || echo "")

# Don't redirect traffic from Tor process itself
if [ -n "$TOR_UID" ]; then
    iptables -t nat -A OUTPUT -m owner --uid-owner "$TOR_UID" -j RETURN
fi

# Redirect DNS queries to Tor DNSPort
iptables -t nat -A OUTPUT -p udp --dport 53 -j REDIRECT --to-ports 5353
iptables -t nat -A OUTPUT -p tcp --dport 53 -j REDIRECT --to-ports 5353

# Redirect all other TCP traffic to Tor TransPort
iptables -t nat -A OUTPUT -p tcp -j REDIRECT --to-ports 9040

echo "iptables configured successfully"

# Start Tor as debian-tor user (not root)
echo "Starting Tor daemon as debian-tor user..."
su -s /bin/bash -c "tor" debian-tor &
TOR_PID=$!

# Wait for Tor to establish circuits
echo "Waiting for Tor to establish circuits..."
sleep 10

echo "Transparent Tor proxy ready"
echo "All network traffic will be routed through Tor"

# Keep container running
wait $TOR_PID
