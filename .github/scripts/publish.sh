#!/usr/bin/env bash
# Trigger the publish-wireguard-go-bridge workflow.
# Version is read from wireguard_go_bridge/__init__.py (single source of truth).
# Usage: .github/scripts/publish.sh
set -euo pipefail

REPO="ARAS-Workspace/phantom-wg"
WORKFLOW="publish-wireguard-go-bridge.yml"
REF="dev/wireguard-go-bridge"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

VERSION=$(python3 -c "
import re, pathlib
text = pathlib.Path('${REPO_ROOT}/wireguard_go_bridge/__init__.py').read_text()
m = re.search(r'__version__\s*=\s*\"(.+?)\"', text)
print('v' + m.group(1))
")

if ! command -v gh &>/dev/null; then
    echo "GitHub CLI (gh) required: brew install gh"
    exit 1
fi

echo "Version : ${VERSION}"
echo "Workflow: ${WORKFLOW}"
echo "Ref     : ${REF}"
echo ""

gh workflow run "$WORKFLOW" \
    --repo "$REPO" \
    --ref "$REF"

echo "Triggered. Watch: gh run list --repo ${REPO} --workflow ${WORKFLOW}"
