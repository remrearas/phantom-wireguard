#!/usr/bin/env bash
# Run cargo commands inside dev container
# Usage: dev/cargo.sh test
#        dev/cargo.sh build --release
#        dev/cargo.sh test --lib db::tests
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
IMAGE_NAME="firewall-bridge-dev:latest"

docker run --rm \
    --privileged \
    --cap-add NET_ADMIN \
    -v "${PROJECT_ROOT}:/workspace" \
    -v "fw-bridge-cargo-cache:/cargo" \
    -w /workspace \
    "${IMAGE_NAME}" \
    cargo "$@"
