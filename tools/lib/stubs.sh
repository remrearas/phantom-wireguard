# ──────────────────────────────────────────────────────────────────
# Vendor type stub generation
# Requires: DAEMON_IMAGE, DAEMON_DOCKERFILE, TOOLS_DIR
# ──────────────────────────────────────────────────────────────────

cmd_stubs() {
    local out_dir="typings"
    local vendor_dir="/opt/phantom/vendor"

    if ! docker image inspect "$DAEMON_IMAGE" &>/dev/null; then
        bold "Image $DAEMON_IMAGE not found. Building..."
        docker build -t "$DAEMON_IMAGE" -f "$DAEMON_DOCKERFILE" .
    fi

    rm -rf "$out_dir"
    mkdir -p "$out_dir"

    bold "Generating type stubs from vendor packages..."
    docker run --rm \
        -v "${TOOLS_DIR}/lib/helpers/gen_stubs.py:/tmp/gen_stubs.py:ro" \
        -v "$(pwd)/$out_dir:/out" \
        "$DAEMON_IMAGE" \
        python /tmp/gen_stubs.py "$vendor_dir" /out

    green "Stubs written to ${out_dir}/"
}
