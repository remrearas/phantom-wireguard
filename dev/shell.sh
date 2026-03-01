#!/usr/bin/env bash
# Interactive shell inside dev container (source mounted)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
IMAGE_NAME="firewall-bridge-dev:latest"
CONTAINER_NAME="fw-bridge-dev-$$"

exec docker run --rm -it \
    --name "${CONTAINER_NAME}" \
    --privileged \
    --cap-add NET_ADMIN \
    --cap-add SYS_ADMIN \
    -v "${PROJECT_ROOT}:/workspace" \
    -v "fw-bridge-cargo-cache:/cargo" \
    -w /workspace \
    -e "FIREWALL_BRIDGE_LIB_PATH=/workspace/target/release/libfirewall_bridge_linux.so" \
    -e "PYTHONPATH=/workspace" \
    "${IMAGE_NAME}" \
    bash
