#!/usr/bin/env bash
# Bump compose-bridge version (patch by default).
#
# Updates BOTH version sources atomically in a single commit:
#   - compose_bridge/__init__.py → __version__
#   - src/version.go             → BridgeVersionStr
#
# Refuses to run if the two files are out of sync (publish workflow
# rejects mismatches anyway; better to catch it here).
#
# Usage:
#   .github/scripts/bump.sh          → 1.0.0 → 1.0.1
#   .github/scripts/bump.sh minor    → 1.0.0 → 1.1.0
#   .github/scripts/bump.sh major    → 1.0.0 → 2.0.0
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
INIT_FILE="${REPO_ROOT}/compose_bridge/__init__.py"
GO_FILE="${REPO_ROOT}/src/version.go"
PART="${1:-patch}"

# ── Extract current versions from both sources ──────────────────────────────

PY_CURRENT=$(python3 -c "
import re, pathlib
text = pathlib.Path('${INIT_FILE}').read_text()
m = re.search(r'__version__\s*=\s*\"(.+?)\"', text)
print(m.group(1))
")

GO_CURRENT=$(python3 -c "
import re, pathlib
text = pathlib.Path('${GO_FILE}').read_text()
m = re.search(r'BridgeVersionStr\s*=\s*\"(.+?)\"', text)
print(m.group(1))
")

# ── Sync check ───────────────────────────────────────────────────────────────

if [[ "$PY_CURRENT" != "$GO_CURRENT" ]]; then
    echo "ERROR: version sources out of sync"
    echo "  __init__.py:    ${PY_CURRENT}"
    echo "  src/version.go: ${GO_CURRENT}"
    echo "Reconcile manually before running bump.sh."
    exit 1
fi

CURRENT="$PY_CURRENT"
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

# ── Apply to both files ──────────────────────────────────────────────────────

python3 -c "
import pathlib
p = pathlib.Path('${INIT_FILE}')
p.write_text(p.read_text().replace('__version__ = \"${CURRENT}\"', '__version__ = \"${NEW}\"'))
"

python3 -c "
import pathlib
p = pathlib.Path('${GO_FILE}')
p.write_text(p.read_text().replace('BridgeVersionStr = \"${CURRENT}\"', 'BridgeVersionStr = \"${NEW}\"'))
"

# ── Verify post-write ────────────────────────────────────────────────────────

PY_NEW=$(python3 -c "
import re, pathlib
text = pathlib.Path('${INIT_FILE}').read_text()
m = re.search(r'__version__\s*=\s*\"(.+?)\"', text)
print(m.group(1))
")

GO_NEW=$(python3 -c "
import re, pathlib
text = pathlib.Path('${GO_FILE}').read_text()
m = re.search(r'BridgeVersionStr\s*=\s*\"(.+?)\"', text)
print(m.group(1))
")

if [[ "$PY_NEW" != "$NEW" || "$GO_NEW" != "$NEW" ]]; then
    echo "ERROR: post-write verification failed"
    echo "  expected:       ${NEW}"
    echo "  __init__.py:    ${PY_NEW}"
    echo "  src/version.go: ${GO_NEW}"
    exit 1
fi

echo "${CURRENT} → ${NEW}"

# ── Commit (both files in one commit) ────────────────────────────────────────

git -C "${REPO_ROOT}" add "${INIT_FILE}" "${GO_FILE}"
git -C "${REPO_ROOT}" commit -m "Bump v${NEW}"

echo ""
echo "Push, then trigger publish: .github/scripts/publish.sh"
