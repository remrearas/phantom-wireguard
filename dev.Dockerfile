# ──────────────────────────────────────────────────────────────────
# phantom-daemon  ·  Development Image
# ──────────────────────────────────────────────────────────────────
# Build:
#   docker build -f dev.Dockerfile -t phantom-daemon:dev .
#   docker build -f dev.Dockerfile --build-arg TARGETARCH=arm64 -t phantom-daemon:dev-arm64 .
#
# Run (remote interpreter):
#   docker run --rm -it phantom-daemon:dev python -c "import phantom_daemon; print(phantom_daemon.__version__)"
# ──────────────────────────────────────────────────────────────────

FROM python:3.12-slim AS base

# ── Build args ───────────────────────────────────────────────────
# TARGETARCH is auto-set by BuildKit (amd64 | arm64).
# Manual override: --build-arg TARGETARCH=arm64
ARG TARGETARCH=amd64

ARG VENDOR_URL=https://vendor-artifacts.phantom.tc
ARG VENDOR_DIR=/opt/phantom/vendor

# ── System deps ──────────────────────────────────────────────────
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl unzip \
 && rm -rf /var/lib/apt/lists/*

# ── Download & unpack vendor pack ────────────────────────────────
RUN set -e; \
    case "${TARGETARCH}" in \
        amd64|arm64) ;; \
        *) echo "Unsupported arch: ${TARGETARCH}" && exit 1 ;; \
    esac; \
    ZIP_NAME="vendor-pack-linux-${TARGETARCH}.zip"; \
    URL="${VENDOR_URL}/${ZIP_NAME}"; \
    echo "Fetching ${URL}"; \
    curl -fSL -o /tmp/vendor-pack.zip "${URL}"; \
    mkdir -p "${VENDOR_DIR}"; \
    unzip -o /tmp/vendor-pack.zip -d "${VENDOR_DIR}"; \
    rm /tmp/vendor-pack.zip

# ── Bridge env vars (.so absolute paths) ─────────────────────────
# _ffi.py 3-tier discovery: env var → sibling → system ldconfig
# Setting env vars = tier-1 hit, zero probing.
ENV WIREGUARD_GO_BRIDGE_LIB_PATH="${VENDOR_DIR}/wireguard_go_bridge/wireguard_go_bridge.so"
ENV FIREWALL_BRIDGE_LIB_PATH="${VENDOR_DIR}/firewall_bridge/libfirewall_bridge_linux.so"
ENV WSTUNNEL_BRIDGE_LIB_PATH="${VENDOR_DIR}/wstunnel_bridge/libwstunnel_bridge_linux.so"

# Make bridge packages importable
ENV PYTHONPATH="${VENDOR_DIR}"

# ── Python deps ──────────────────────────────────────────────────
WORKDIR /app

COPY requirements.txt requirements-test.txt ./
RUN pip install --no-cache-dir -r requirements-test.txt

# ── Application source ───────────────────────────────────────────
COPY phantom_daemon/ phantom_daemon/
COPY tests/ tests/
COPY pytest.ini ./

# ── Runtime defaults ─────────────────────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

CMD ["python"]
