FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    wireguard-tools \
    iproute2 \
    iputils-ping \
    curl \
    bash \
    && rm -rf /var/lib/apt/lists/*

# wstunnel binary (client mode)
COPY tests/assets/ /tmp/wstunnel/
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then ARCH="amd64"; \
    elif [ "$ARCH" = "aarch64" ]; then ARCH="arm64"; fi && \
    tar -xzf /tmp/wstunnel/wstunnel_10.5.2_linux_${ARCH}.tar.gz \
      -C /usr/local/bin/ && \
    chmod +x /usr/local/bin/wstunnel && \
    rm -rf /tmp/wstunnel

CMD ["sleep", "infinity"]
