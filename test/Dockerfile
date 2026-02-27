FROM golang:1.25-bookworm AS builder

WORKDIR /build
COPY src/ /build/
RUN CGO_ENABLED=1 \
    go build -buildmode=c-shared -trimpath -ldflags="-s -w" \
    -o /wireguard_go_bridge.so .

FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    wireguard-tools \
    iproute2 \
    iptables \
    iputils-ping \
    net-tools \
    procps \
    kmod \
    iperf3 \
    ncat \
    nmap \
    bash \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY --from=builder /wireguard_go_bridge.so /workspace/wireguard_go_bridge.so
COPY wireguard_go_bridge/ /workspace/wireguard_go_bridge/
COPY test/ /workspace/test/

RUN chmod +x test/test.sh test/bridge_program.py

ENV WIREGUARD_GO_BRIDGE_LIB_PATH=/workspace/wireguard_go_bridge.so
ENV PYTHONPATH=/workspace

CMD ["sleep", "infinity"]