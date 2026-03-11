FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    wireguard-tools iproute2 iputils-ping curl bash openresolv procps iptables nftables \
    && rm -rf /var/lib/apt/lists/*

CMD ["sleep", "infinity"]
