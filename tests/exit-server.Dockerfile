FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    wireguard-tools \
    iproute2 \
    iptables \
    iputils-ping \
    procps \
    bash \
    && rm -rf /var/lib/apt/lists/*

COPY tests/exit-server-init.sh /init.sh
RUN chmod +x /init.sh

CMD ["/init.sh"]
