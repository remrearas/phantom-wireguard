# ──────────────────────────────────────────────────────────────────
# Production package generator
# Requires: TOOLS_DIR
# ──────────────────────────────────────────────────────────────────

cmd_generate_production_package() {
    bold "Building React SPA..."
    (cd services/react-spa && npm run build)
    green "SPA built → services/react-spa/dist/"

    bold "Generating production package..."
    python3 "${TOOLS_DIR}/lib/helpers/packager.py" --clean
    green "Production package ready → dist/phantom-wg-modern/"
}
