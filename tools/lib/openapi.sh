# ──────────────────────────────────────────────────────────────────
# OpenAPI schema export
# Requires: COMPOSE, DAEMON
# ──────────────────────────────────────────────────────────────────

cmd_openapi() {
    bold "Exporting OpenAPI schema..."
    $COMPOSE exec "$DAEMON" python -c "
import json
from phantom_daemon.main import create_app
app = create_app(lifespan_func=None)
print(json.dumps(app.openapi(), indent=2))
" > openapi.json
    green "Written to openapi.json"
}
