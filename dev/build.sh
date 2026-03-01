#!/usr/bin/env bash
# Build the dev container image
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
IMAGE_NAME="firewall-bridge-dev:latest"

echo "Building dev container: ${IMAGE_NAME}"
docker build \
    -t "${IMAGE_NAME}" \
    -f "${SCRIPT_DIR}/Dockerfile" \
    "${PROJECT_ROOT}"

echo "Done: ${IMAGE_NAME}"
