# ──────────────────────────────────────────────────────────────────
# Test runners — unit, UDS, E2E
# Requires: COMPOSE, DAEMON
# ──────────────────────────────────────────────────────────────────

cmd_test() {
    bold "Running pytest (ASGI mode, excluding slow)..."
    if [ $# -eq 0 ]; then
        $COMPOSE exec "$DAEMON" python -m pytest tests/ -v -s -m "not slow"
    else
        $COMPOSE exec "$DAEMON" python -m pytest -v -s -m "not slow" "$@"
    fi
}

cmd_test_full() {
    bold "Running pytest (ASGI mode, all tests)..."
    if [ $# -eq 0 ]; then
        $COMPOSE exec "$DAEMON" python -m pytest tests/ -v -s
    else
        $COMPOSE exec "$DAEMON" python -m pytest -v -s "$@"
    fi
}

cmd_test_uds() {
    bold "Running pytest (UDS mode)..."
    if [ $# -eq 0 ]; then
        $COMPOSE exec "$DAEMON" python -m pytest tests/ -v --uds /var/run/phantom/daemon.sock
    else
        $COMPOSE exec "$DAEMON" python -m pytest -v --uds /var/run/phantom/daemon.sock "$@"
    fi
}

# ── E2E helpers ──────────────────────────────────────────────────

_require_compose_bridge() {
    if [ ! -d "lib/compose_bridge" ] || [ -z "$(ls lib/compose_bridge/*.so lib/compose_bridge/*.dylib 2>/dev/null)" ]; then
        red "compose-bridge not found. Run: ./tools/dev.sh fetch-compose-bridge"
        exit 1
    fi
}

_run_e2e() {
    local runner="$1"; shift
    _require_compose_bridge
    local lib_file
    lib_file="$(find lib/compose_bridge -maxdepth 1 \( -name '*.dylib' -o -name '*.so' \) -print -quit)"
    COMPOSE_BRIDGE_LIB_PATH="$(pwd)/${lib_file}" \
    PYTHONPATH="$(pwd)/lib:${PYTHONPATH:-}" \
    python3 "$runner" "$@"
}

cmd_test_multihop_e2e() {
    bold "Running multihop E2E tests..."
    _run_e2e e2e_tests/multihop/runner.py "$@"
}

cmd_test_chaos_e2e() {
    bold "Running chaos E2E tests..."
    _run_e2e e2e_tests/chaos/runner.py "$@"
}

cmd_test_scenario_e2e() {
    bold "Running scenario E2E tests..."
    _run_e2e e2e_tests/scenario/runner.py "$@"
}

cmd_fetch_compose_bridge() {
    local repo="ARAS-Workspace/phantom-wg"
    local run_id="22726661393"
    local version="1.0.0"
    local dest="lib/compose_bridge"

    local os arch
    os="$(uname -s | tr '[:upper:]' '[:lower:]')"
    arch="$(uname -m)"
    case "$arch" in
        x86_64)  arch="amd64" ;;
        aarch64) arch="arm64" ;;
        arm64)   arch="arm64" ;;
        *)       red "Unsupported architecture: $arch"; exit 1 ;;
    esac

    local artifact_name="compose-bridge-${version}-${os}-${arch}"

    if ! command -v gh &>/dev/null; then
        red "GitHub CLI (gh) required: brew install gh"
        exit 1
    fi

    if ! gh auth status &>/dev/null; then
        red "Not authenticated. Run: gh auth login"
        exit 1
    fi

    bold "Fetching ${artifact_name}..."

    rm -rf "$dest"
    mkdir -p "$dest"

    local tmp_dir
    tmp_dir="$(mktemp -d)"

    gh run download "$run_id" \
        --repo "$repo" \
        --name "$artifact_name" \
        --dir "$tmp_dir"

    local zip_file="$tmp_dir/${artifact_name}.zip"
    if [ -f "$zip_file" ]; then
        unzip -o "$zip_file" -d "$tmp_dir/extracted"
        cp "$tmp_dir/extracted/compose_bridge/"* "$dest/"
    else
        cp "$tmp_dir/"* "$dest/" 2>/dev/null || true
    fi

    rm -rf "$tmp_dir"

    green "Installed to ${dest}/"
    ls -lh "$dest/"
}
