#!/bin/bash
# ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
# ██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
# ██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
# ██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
# ██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
# ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
#
# Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
# Licensed under AGPL-3.0 - see LICENSE file for details
# Third-party licenses - see THIRD_PARTY_LICENSES file for details
# WireGuard® is a registered trademark of Jason A. Donenfeld.

#
# wireguard-go-bridge integration test wrapper
#
# Runs the upstream wireguard-go netns.sh test using our Python FFI
# bridge as a drop-in replacement for the wireguard-go binary.
#
# Source: https://git.zx2c4.com/wireguard-go/tree/tests/netns.sh
#
# Usage (requires Linux, root):
#   sudo ./test.sh [path-to-wireguard_go_bridge.so]

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LIB_PATH="${1:-${SCRIPT_DIR}/../lib/linux-amd64/wireguard_go_bridge.so}"
NETNS="${SCRIPT_DIR}/netns.sh"

if [[ ! -f "$LIB_PATH" ]]; then
    # Fallback: container build path
    LIB_PATH="/workspace/wireguard_go_bridge.so"
fi

if [[ ! -f "$LIB_PATH" ]]; then
    echo "ERROR: wireguard_go_bridge.so not found"
    echo "Usage: sudo $0 [path-to-wireguard_go_bridge.so]"
    exit 1
fi

if [[ $EUID -ne 0 ]]; then
    echo "ERROR: This test requires root privileges (network namespaces, TUN)"
    echo "Usage: sudo $0"
    exit 1
fi

export WIREGUARD_GO_BRIDGE_LIB_PATH="$LIB_PATH"
export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH}"

# Create a wireguard-go compatible wrapper that upstream netns.sh
# will invoke as: $program <interface-name>
WRAPPER=$(mktemp /tmp/wireguard-go-bridge-XXXXXX)
cat > "$WRAPPER" << EOF
#!/bin/bash
python3 "${SCRIPT_DIR}/bridge_program.py" "\$@" &
while ! ip link show "\$1" >/dev/null 2>&1; do sleep 0.1; done
EOF
chmod +x "$WRAPPER"

trap 'rm -f "$WRAPPER"' EXIT

echo "[+] wireguard_go_bridge.so: $LIB_PATH"
echo "[+] wrapper: $WRAPPER"
echo "[+] Running netns.sh..."
echo ""

exec "$NETNS" "$WRAPPER"