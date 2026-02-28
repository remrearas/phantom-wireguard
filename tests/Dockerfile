FROM golang:1.25-bookworm AS builder

RUN apt-get update && apt-get install -y --no-install-recommends libsqlite3-dev

WORKDIR /build
COPY src/ /build/
RUN CGO_ENABLED=1 \
    go build -buildmode=c-shared -trimpath -ldflags="-s -w" \
    -o /wireguard_go_bridge.so .

FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    wireguard-tools \
    iproute2 \
    iptables \
    iputils-ping \
    net-tools \
    procps \
    kmod \
    sqlite3 \
    iperf3 \
    ncat \
    bash \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages pytest pytest-cov

WORKDIR /workspace

COPY --from=builder /wireguard_go_bridge.so /workspace/wireguard_go_bridge.so
COPY wireguard_go_bridge/ /workspace/wireguard_go_bridge/
COPY tests/ /workspace/tests/
COPY pytest.ini /workspace/pytest.ini

# Legacy netns test files (v1 shell-based tunnel tests)
COPY tests/netns-test/ /workspace/tests/netns-test/

ENV WIREGUARD_GO_BRIDGE_LIB_PATH=/workspace/wireguard_go_bridge.so
ENV PYTHONPATH=/workspace

CMD ["sleep", "infinity"]
