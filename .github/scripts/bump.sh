#!/usr/bin/env bash
# Bump firewall-bridge version (patch by default).
#
# Updates ALL version locations atomically in a single commit:
#   - firewall_bridge/__init__.py → __version__
#   - Cargo.toml                  → [package] version
#   - Cargo.lock                  → [[package]] firewall-bridge-linux version
#
# Refuses to run if any of the three are out of sync (publish workflow
# rejects mismatches anyway; better to catch it here).
#
# Usage:
#   .github/scripts/bump.sh          → 2.1.4 → 2.1.5
#   .github/scripts/bump.sh minor    → 2.1.4 → 2.2.0
#   .github/scripts/bump.sh major    → 2.1.4 → 3.0.0
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
INIT_FILE="${REPO_ROOT}/firewall_bridge/__init__.py"
CARGO_FILE="${REPO_ROOT}/Cargo.toml"
LOCK_FILE="${REPO_ROOT}/Cargo.lock"
PART="${1:-patch}"

# ── Extract current versions from both sources ──────────────────────────────

PY_CURRENT=$(python3 -c "
import re, pathlib
text = pathlib.Path('${INIT_FILE}').read_text()
m = re.search(r'__version__\s*=\s*\"(.+?)\"', text)
print(m.group(1))
")

# Anchor on '^version' (line start, MULTILINE) so dependency versions
# elsewhere in Cargo.toml cannot match. Take only the first occurrence.
RUST_CURRENT=$(python3 -c "
import re, pathlib
text = pathlib.Path('${CARGO_FILE}').read_text()
m = re.search(r'^version\s*=\s*\"(.+?)\"', text, re.MULTILINE)
print(m.group(1))
")

# Cargo.lock has many [[package]] blocks. Match the version line that
# immediately follows our package's name line — and only that one.
LOCK_CURRENT=$(python3 -c "
import re, pathlib
text = pathlib.Path('${LOCK_FILE}').read_text()
m = re.search(r'name = \"firewall-bridge-linux\"\nversion = \"(.+?)\"', text)
print(m.group(1))
")

# ── Sync check ───────────────────────────────────────────────────────────────

if [[ "$PY_CURRENT" != "$RUST_CURRENT" || "$PY_CURRENT" != "$LOCK_CURRENT" ]]; then
    echo "ERROR: version sources out of sync"
    echo "  __init__.py:  ${PY_CURRENT}"
    echo "  Cargo.toml:   ${RUST_CURRENT}"
    echo "  Cargo.lock:   ${LOCK_CURRENT}"
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

# Anchored substitution on Cargo.toml — replaces only the first
# line-start 'version = ...' so transitive dependency versions are safe.
python3 -c "
import re, pathlib
p = pathlib.Path('${CARGO_FILE}')
text = p.read_text()
new = re.sub(r'^version\s*=\s*\".+?\"', 'version = \"${NEW}\"', text, count=1, flags=re.MULTILINE)
p.write_text(new)
"

# Cargo.lock — only the version line directly under our package's name.
# Pure version field; no checksums are affected by this rename.
python3 -c "
import re, pathlib
p = pathlib.Path('${LOCK_FILE}')
text = p.read_text()
new = re.sub(
    r'(name = \"firewall-bridge-linux\"\nversion = )\".+?\"',
    r'\1\"${NEW}\"',
    text,
)
p.write_text(new)
"

# ── Verify post-write ────────────────────────────────────────────────────────

PY_NEW=$(python3 -c "
import re, pathlib
text = pathlib.Path('${INIT_FILE}').read_text()
m = re.search(r'__version__\s*=\s*\"(.+?)\"', text)
print(m.group(1))
")

RUST_NEW=$(python3 -c "
import re, pathlib
text = pathlib.Path('${CARGO_FILE}').read_text()
m = re.search(r'^version\s*=\s*\"(.+?)\"', text, re.MULTILINE)
print(m.group(1))
")

LOCK_NEW=$(python3 -c "
import re, pathlib
text = pathlib.Path('${LOCK_FILE}').read_text()
m = re.search(r'name = \"firewall-bridge-linux\"\nversion = \"(.+?)\"', text)
print(m.group(1))
")

if [[ "$PY_NEW" != "$NEW" || "$RUST_NEW" != "$NEW" || "$LOCK_NEW" != "$NEW" ]]; then
    echo "ERROR: post-write verification failed"
    echo "  expected:     ${NEW}"
    echo "  __init__.py:  ${PY_NEW}"
    echo "  Cargo.toml:   ${RUST_NEW}"
    echo "  Cargo.lock:   ${LOCK_NEW}"
    exit 1
fi

echo "${CURRENT} → ${NEW}"

# ── Commit (all three files in one commit) ───────────────────────────────────

git -C "${REPO_ROOT}" add "${INIT_FILE}" "${CARGO_FILE}" "${LOCK_FILE}"
git -C "${REPO_ROOT}" commit -m "Bump v${NEW}"

echo ""
echo "Push, then trigger publish: .github/scripts/publish.sh"
