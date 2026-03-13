# ──────────────────────────────────────────────────────────────────
# Database & state management (development)
# Requires: COMPOSE, DAEMON, SECRETS_DIR
# ──────────────────────────────────────────────────────────────────

cmd_db_ls() {
    bold "Local db/ contents:"
    ls -lah container-data/db/ 2>/dev/null || red "db/ is empty or missing"
}

cmd_db_ls_r() {
    bold "Container db/ contents:"
    $COMPOSE exec "$DAEMON" ls -lah /var/lib/phantom/db/ 2>/dev/null || red "No db files in container"
}

cmd_db_reset() {
    bold "Wiping db/ + auth-db/..."
    rm -rf container-data/db/*
    rm -f container-data/auth-db/auth.db container-data/auth-db/auth.db-wal container-data/auth-db/auth.db-shm
    green "db/ + auth-db/ cleared."
}

cmd_state_reset() {
    bold "Wiping state/db/..."
    rm -rf container-data/state/db/*
    green "state/db cleared."
}

cmd_key_reset() {
    bold "Wiping development secrets..."
    find "${SECRETS_DIR}" -type f ! -name '.gitkeep' -delete
    green "${SECRETS_DIR}/ cleared (gitkeep preserved)."
}
