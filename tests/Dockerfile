FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    wireguard-tools \
    iproute2 \
    iptables \
    iputils-ping \
    procps \
    openssl \
    sqlite3 \
    bash \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY requirements.txt /workspace/requirements.txt
RUN pip3 install --break-system-packages -r requirements.txt

# .so (FFI library — wstunnel server runs via FFI, no CLI binary needed)
COPY dist/ /tmp/dist/
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then ARCH="amd64"; \
    elif [ "$ARCH" = "aarch64" ]; then ARCH="arm64"; fi && \
    cp /tmp/dist/linux-${ARCH}/libwstunnel_bridge_linux.so /workspace/ && \
    rm -rf /tmp/dist

# Self-signed TLS cert
RUN mkdir -p /certs && \
    openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 \
    -keyout /certs/key.pem -out /certs/cert.pem \
    -days 365 -nodes -subj "/CN=localhost" 2>/dev/null

ENV WSTUNNEL_BRIDGE_LIB_PATH=/workspace/libwstunnel_bridge_linux.so
ENV PYTHONPATH=/workspace

CMD ["sleep", "infinity"]
