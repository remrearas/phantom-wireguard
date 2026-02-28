FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    socat \
    ncat \
    openssl \
    procps \
    bash \
    tar \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Copy both arch wstunnel binaries, install matching one
COPY test/artifacts/wstunnel_10.5.2_linux_amd64.tar.gz /tmp/
COPY test/artifacts/wstunnel_10.5.2_linux_arm64.tar.gz /tmp/
RUN ARCH=$(dpkg --print-architecture) && \
    tar xzf /tmp/wstunnel_10.5.2_linux_${ARCH}.tar.gz -C /usr/local/bin/ wstunnel && \
    chmod +x /usr/local/bin/wstunnel && \
    rm /tmp/wstunnel_10.5.2_linux_*.tar.gz && \
    wstunnel --version

# Copy matching .so for runtime arch
COPY dist/linux-amd64/libwstunnel_bridge_linux.so /tmp/lib-amd64.so
COPY dist/linux-arm64/libwstunnel_bridge_linux.so /tmp/lib-arm64.so
RUN ARCH=$(dpkg --print-architecture) && \
    cp /tmp/lib-${ARCH}.so /workspace/libwstunnel_bridge_linux.so && \
    rm /tmp/lib-*.so

COPY wstunnel_bridge/ /workspace/wstunnel_bridge/
COPY test/ /workspace/test/

RUN mkdir -p /workspace/certs && \
    openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 \
    -keyout /workspace/certs/key.pem -out /workspace/certs/cert.pem \
    -days 365 -nodes -subj "/CN=localhost" 2>/dev/null

ENV WSTUNNEL_BRIDGE_LIB_PATH=/workspace/libwstunnel_bridge_linux.so
ENV PYTHONPATH=/workspace

CMD ["sleep", "infinity"]
