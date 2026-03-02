FROM rust:1.85-bookworm AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    libnftables-dev libmnl-dev

WORKDIR /build
COPY Cargo.toml Cargo.lock build.rs /build/
COPY src/ /build/src/
RUN cargo build --release \
    && cp target/release/libfirewall_bridge_linux.so /libfirewall_bridge_linux.so

FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    wireguard-tools \
    nftables \
    iproute2 \
    iptables \
    iputils-ping \
    procps \
    sqlite3 \
    bash \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY requirements.txt /workspace/requirements.txt
RUN pip3 install --break-system-packages -r requirements.txt

COPY --from=builder /libfirewall_bridge_linux.so /workspace/libfirewall_bridge_linux.so

ENV FIREWALL_BRIDGE_LIB_PATH=/workspace/libfirewall_bridge_linux.so
ENV PYTHONPATH=/workspace

CMD ["sleep", "infinity"]
