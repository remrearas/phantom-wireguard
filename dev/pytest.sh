#!/usr/bin/env bash
# Run Python tests inside dev container
# Usage: dev/pytest.sh                      # all tests
#        dev/pytest.sh test/test_types.py   # specific test
#        dev/pytest.sh --docker             # integration tests
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
IMAGE_NAME="firewall-bridge-dev:latest"

# Build .so first
echo "=== Building libfirewall_bridge_linux.so ==="
docker run --rm \
    --privileged \
    -v "${PROJECT_ROOT}:/workspace" \
    -v "fw-bridge-cargo-cache:/cargo" \
    -w /workspace \
    "${IMAGE_NAME}" \
    cargo build --release

echo "=== Running pytest ==="
docker run --rm \
    --privileged \
    --cap-add NET_ADMIN \
    --cap-add SYS_ADMIN \
    -v "${PROJECT_ROOT}:/workspace" \
    -v "fw-bridge-cargo-cache:/cargo" \
    -w /workspace \
    -e "FIREWALL_BRIDGE_LIB_PATH=/workspace/target/release/libfirewall_bridge_linux.so" \
    -e "PYTHONPATH=/workspace" \
    "${IMAGE_NAME}" \
    python3 -m pytest "$@" -v --tb=short
