FROM debian:bookworm-slim

ARG TARGETARCH

RUN apt-get update && apt-get install -y --no-install-recommends \
    wireguard-tools iproute2 iputils-ping curl bash openresolv \
    && rm -rf /var/lib/apt/lists/*

# wstunnel binary for ghost mode E2E
COPY e2e_tests/assets/wstunnel_10.5.2_linux_${TARGETARCH}.tar.gz /tmp/wstunnel.tar.gz
RUN tar -xzf /tmp/wstunnel.tar.gz -C /usr/local/bin wstunnel \
    && chmod +x /usr/local/bin/wstunnel \
    && rm /tmp/wstunnel.tar.gz

CMD ["sleep", "infinity"]
