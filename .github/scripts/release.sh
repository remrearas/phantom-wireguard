#!/usr/bin/env bash
# Trigger the mac-release workflow.
# Version is read from project.yml MARKETING_VERSION (single source of truth).
# Creates mac-v{version} tag and pushes it.
# Usage: .github/scripts/release.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PROJECT_YML="${REPO_ROOT}/project.yml"

VERSION=$(grep -m1 'MARKETING_VERSION:' "$PROJECT_YML" | sed 's/.*"\(.*\)"/\1/')

if [[ -z "$VERSION" ]]; then
    echo "ERROR: Could not find MARKETING_VERSION in project.yml"
    exit 1
fi

TAG="mac-v${VERSION}"

echo "Version : ${VERSION}"
echo "Tag     : ${TAG}"
echo ""

# Check if tag already exists
if git -C "${REPO_ROOT}" rev-parse "${TAG}" &>/dev/null 2>&1; then
    echo "Tag ${TAG} already exists locally."
    printf "Delete and recreate? [y/N]: "
    read -r confirm
    if [[ "$confirm" != "y" ]]; then
        echo "Aborted."
        exit 1
    fi
    git -C "${REPO_ROOT}" tag -d "${TAG}"
    git -C "${REPO_ROOT}" push origin ":refs/tags/${TAG}" 2>/dev/null || true
fi

git -C "${REPO_ROOT}" tag "${TAG}"
git -C "${REPO_ROOT}" push origin "${TAG}"

echo ""
echo "Release triggered: ${TAG}"
echo "Watch: gh run list --workflow mac-release.yml"
