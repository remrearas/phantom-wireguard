#!/usr/bin/env bash
# Fetch compose-bridge for current platform
# Usage: bash fetch_compose_bridge.sh

set -euo pipefail

REPO="ARAS-Workspace/phantom-wg"
RUN_ID="22726661393"
VERSION="1.0.0"
DEST="lib/compose_bridge"

OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"
case "$ARCH" in
    x86_64)  ARCH="amd64" ;;
    aarch64) ARCH="arm64" ;;
    arm64)   ARCH="arm64" ;;
    *)       echo "Unsupported architecture: $ARCH"; exit 1 ;;
esac

ARTIFACT_NAME="compose-bridge-${VERSION}-${OS}-${ARCH}"

if ! command -v gh &>/dev/null; then
    echo "GitHub CLI (gh) required: brew install gh"
    exit 1
fi

if ! gh auth status &>/dev/null; then
    echo "Not authenticated. Run: gh auth login"
    exit 1
fi

echo "Fetching ${ARTIFACT_NAME}..."

rm -rf "$DEST"
mkdir -p "$DEST"

TMP_DIR="$(mktemp -d)"

gh run download "$RUN_ID" \
    --repo "$REPO" \
    --name "$ARTIFACT_NAME" \
    --dir "$TMP_DIR"

ZIP_FILE="$TMP_DIR/${ARTIFACT_NAME}.zip"
if [ -f "$ZIP_FILE" ]; then
    unzip -o "$ZIP_FILE" -d "$TMP_DIR/extracted"
    cp "$TMP_DIR/extracted/compose_bridge/"* "$DEST/"
else
    cp "$TMP_DIR/"* "$DEST/" 2>/dev/null || true
fi

rm -rf "$TMP_DIR"

echo "Installed to ${DEST}/"
ls -lh "$DEST/"
