#!/usr/bin/env bash
# Bump auth-service version (patch by default).
#
# auth_service/__init__.py is the single source of truth — there is no
# Go/Rust counterpart to keep in sync. Updating just __version__ and
# committing is enough; the package workflow re-reads from this file.
#
# Usage:
#   .github/scripts/bump.sh          → 1.1.1 → 1.1.2
#   .github/scripts/bump.sh minor    → 1.1.1 → 1.2.0
#   .github/scripts/bump.sh major    → 1.1.1 → 2.0.0
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
INIT_FILE="${REPO_ROOT}/auth_service/__init__.py"
PART="${1:-patch}"

# ── Extract current version ─────────────────────────────────────────────────

CURRENT=$(python3 -c "
import re, pathlib
text = pathlib.Path('${INIT_FILE}').read_text()
m = re.search(r'__version__\s*=\s*\"(.+?)\"', text)
print(m.group(1))
")

IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT"

case "$PART" in
    major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0 ;;
    minor) MINOR=$((MINOR + 1)); PATCH=0 ;;
    patch) PATCH=$((PATCH + 1)) ;;
    *)
        echo "Usage: bump.sh [major|minor|patch]"
        exit 1
        ;;
esac

NEW="${MAJOR}.${MINOR}.${PATCH}"

# ── Write new version ────────────────────────────────────────────────────────

python3 -c "
import pathlib
p = pathlib.Path('${INIT_FILE}')
p.write_text(p.read_text().replace('__version__ = \"${CURRENT}\"', '__version__ = \"${NEW}\"'))
"

# ── Verify post-write ────────────────────────────────────────────────────────

NEW_VERIFIED=$(python3 -c "
import re, pathlib
text = pathlib.Path('${INIT_FILE}').read_text()
m = re.search(r'__version__\s*=\s*\"(.+?)\"', text)
print(m.group(1))
")

if [[ "$NEW_VERIFIED" != "$NEW" ]]; then
    echo "ERROR: post-write verification failed"
    echo "  expected:    ${NEW}"
    echo "  __init__.py: ${NEW_VERIFIED}"
    exit 1
fi

echo "${CURRENT} → ${NEW}"

# ── Commit ───────────────────────────────────────────────────────────────────

git -C "${REPO_ROOT}" add "${INIT_FILE}"
git -C "${REPO_ROOT}" commit -m "Bump v${NEW}"

echo ""
echo "Push, then trigger packaging: .github/scripts/package.sh"
